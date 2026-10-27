from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from obscript.agent import AgentError
from obscript.opencode_agent import OpenCodeAgent, OpenCodeHarness
from obscript.post_production import PostProductionAgent
from obscript.production import ProductionAgent, ProductionError
from obscript.storage import read_json
from test_visual_production import REPO, config_fixture, script_fixture, story_fixture


def text_event(text, message='message-1', part='part-1'):
    return json.dumps({'type': 'text', 'part': {'id': part, 'messageID': message, 'text': text}}) + '\n'


def knowledge_fixture():
    return {
        'schema_version': '1', 'kind': 'single',
        'sources': [{'id': 'source-01', 'title': 'Fonte', 'source': 'source',
                     'language': 'pt-BR', 'duration_seconds': 12}],
        'summary': {'thesis': 'Tese', 'objective': 'Explicar'},
        'topics': [], 'relationships': [], 'source_order': ['source-01'],
        'narrative': {'format': 'source', 'hook_intent': 'Gancho', 'conclusion_intent': 'Conclusão', 'ordered_topic_ids': [],
                      'transition_intents': []},
        'recommended_duration_seconds': 12,
    }


class OpenCodeAgentTests(unittest.TestCase):
    def test_research_permissions_are_scoped_to_the_initial_review(self):
        with patch.dict(os.environ, {"OPENCODE_CONFIG_CONTENT": "{}"}):
            harness = OpenCodeHarness(Path("opencode"), REPO)
            ordinary = json.loads(harness.environment()["OPENCODE_CONFIG_CONTENT"])["permission"]
            research = json.loads(harness.environment(web_search=True)["OPENCODE_CONFIG_CONTENT"])["permission"]
        self.assertNotIn("websearch", ordinary)
        self.assertEqual(research["websearch"], "allow")
        self.assertEqual(research["webfetch"], "allow")
        self.assertEqual(research["*"], "deny")
        self.assertNotIn("bash", research)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.agent = OpenCodeAgent(executable=Path('opencode'), repo_root=REPO,
                                   project_root=self.root, model=None,
                                   reasoning_effort='medium', verbose=False)

    def run_agent(self, stdout, *, schema='script', skill='write-script', returncode=0):
        with patch('obscript.opencode_agent.subprocess.run', return_value=
                   subprocess.CompletedProcess([], returncode, stdout, 'diagnostics')) as run:
            result = self.agent.run(stage=skill, skill=skill, schema=schema, prompt='Execute the stage.')
        return result, run.call_args

    def test_native_defaults_schema_handoff_and_read_only_permissions(self):
        (value, output), call = self.run_agent(text_event(json.dumps(script_fixture())))
        self.assertEqual(value, script_fixture())
        self.assertEqual(read_json(output), value)
        command = call.args[0]
        self.assertEqual(command[:4], ['opencode', 'run', '--format', 'json'])
        self.assertEqual(call.kwargs['cwd'], self.root)
        self.assertEqual(call.kwargs['env']['PWD'], str(self.root.resolve()))
        self.assertIn('--standalone', command)
        self.assertNotIn('--dir', command)
        for flag in ['--model', '--variant', '--agent', '--sandbox', '--output-schema']:
            self.assertNotIn(flag, command)
        self.assertIn('All natural-language fields must be written in Brazilian Portuguese', call.kwargs['input'])
        self.assertIn(str(REPO / 'skills/write-script/SKILL.md'), call.kwargs['input'])
        self.assertIn('Output JSON Schema:', call.kwargs['input'])
        config = json.loads(call.kwargs['env']['OPENCODE_CONFIG_CONTENT'])
        self.assertEqual(config['permission']['*'], 'deny')
        self.assertEqual(config['permission']['read'], 'allow')
        self.assertIn(str(REPO / 'skills'), config['skills']['paths'])
        self.assertTrue(output.with_suffix('.executor.log').exists())

    def test_storybook_language_is_preserved(self):
        (value, _), call = self.run_agent(text_event(json.dumps(story_fixture())),
                                         schema='storybook', skill='storybook')
        self.assertEqual(value, story_fixture())
        self.assertIn('instructions in English', call.kwargs['input'])
        self.assertIn('Preserve voiceover.text verbatim', call.kwargs['input'])

    def test_fences_and_final_message_ignore_progress_and_tool_events(self):
        stream = text_event('Reading the inputs.', 'progress')
        stream += json.dumps({'type': 'tool_use', 'part': {'text': 'not a response'}}) + '\n'
        stream += text_event('```json\n' + json.dumps(script_fixture()) + '\n```', 'final')
        (value, _), _ = self.run_agent(stream)
        self.assertEqual(value, script_fixture())

    def test_local_refs_and_split_schema_are_validated(self):
        knowledge = knowledge_fixture()
        (value, _), _ = self.run_agent(text_event(json.dumps(knowledge)), schema='knowledge', skill='analyze-source')
        self.assertEqual(value, knowledge)
        split = {'rationale': 'Partes independentes', 'parts': [knowledge, knowledge]}
        (value, _), _ = self.run_agent(text_event(json.dumps(split)), schema='split', skill='split')
        self.assertEqual(value, split)
        knowledge['sources'][0]['duration_seconds'] = -1
        with self.assertRaisesRegex(AgentError, 'below minimum'):
            self.run_agent(text_event(json.dumps(split)), schema='split', skill='split')

    def test_bad_structure_never_publishes_a_checkpoint(self):
        for value in [{}, [], {**script_fixture(), 'language': 'en'},
                      {**script_fixture(), 'unexpected': 'field'},
                      {**script_fixture(), 'sections': script_fixture()['sections'][:1]}]:
            with self.subTest(value=value), self.assertRaises(AgentError):
                self.run_agent(text_event(json.dumps(value)))
        self.assertFalse(list(self.root.glob('.obscript/*-write-script.json')))
        script = script_fixture()
        script['metadata']['format'] = 'unknown'
        with self.assertRaisesRegex(AgentError, 'expected one of'):
            self.run_agent(text_event(json.dumps(script)))

    def test_errors_and_empty_or_malformed_streams_are_reported(self):
        streams = ['', 'not json', text_event('not JSON'),
                   json.dumps({'type': 'error', 'error': {'data': {'message': 'provider failed'}}})]
        for stream in streams:
            with self.subTest(stream=stream), self.assertRaises(AgentError):
                self.run_agent(stream)
        with self.assertRaisesRegex(AgentError, 'exit 3'):
            self.run_agent('', returncode=3)
        with patch('obscript.opencode_agent.subprocess.run', side_effect=FileNotFoundError('missing')):
            with self.assertRaisesRegex(AgentError, 'could not start'):
                self.agent.run(stage='write-script', skill='write-script', schema='script', prompt='Write.')

    def test_explicit_model_override(self):
        self.agent.model = 'provider/model'
        (_, _), call = self.run_agent(text_event(json.dumps(script_fixture())))
        command = call.args[0]
        self.assertEqual(command[command.index('--model') + 1], 'provider/model')
        self.assertNotIn('--variant', command)

    def test_nonzero_exit_preserves_provider_auth_error(self):
        stream = json.dumps({'type': 'error', 'error': {
            'type': 'provider.auth', 'message': 'User not found.', 'status': 401,
            'response': {'body': 'raw provider response'},
        }})
        with self.assertRaisesRegex(AgentError, r'provider.auth \(HTTP 401\): User not found\.'):
            self.run_agent(stream, returncode=1)

    def test_shared_counter_allows_switching_harnesses(self):
        self.run_agent(text_event(json.dumps(script_fixture())))
        other = OpenCodeAgent(executable=Path('opencode'), repo_root=REPO,
                              project_root=self.root, model=None, reasoning_effort='high', verbose=False)
        self.assertEqual(other._counter, 1)


class OpenCodeExecutionTests(unittest.TestCase):
    def test_error_detail_supports_v1_v2_and_stderr_fallback(self):
        cases = [
            ('not JSON\n', None),
            (text_event('Progress'), None),
            (json.dumps({'type': 'error', 'error': 'failed'}), 'failed'),
            (json.dumps({'type': 'error', 'error': {'name': 'APIError',
                        'data': {'message': 'Provider failed', 'statusCode': 503}}}),
             'APIError (HTTP 503): Provider failed'),
            (json.dumps({'type': 'error', 'error': {'type': 'provider.auth',
                        'message': 'User not found.', 'status': 401, 'response': {'body': 'omit'}}}),
             'provider.auth (HTTP 401): User not found.'),
        ]
        for stream, expected in cases:
            with self.subTest(stream=stream):
                self.assertEqual(OpenCodeHarness.error_detail(stream), expected)

    @patch('obscript.production.ensure_runtime')
    def test_subprocess_handoff_without_running_opencode(self, ensure_runtime):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            executable = root / 'fake-opencode'
            executable.write_text(
                f'#!{sys.executable}\n'
                'import json, os, sys\n'
                "assert sys.argv[1:] == ['run', '--format', 'json', '--standalone']\n"
                "assert os.environ['PWD'] == os.getcwd()\n"
                "config = json.loads(os.environ['OPENCODE_CONFIG_CONTENT'])\n"
                "assert config['skills']['paths']\n"
                'prompt = sys.stdin.read()\n'
                "assert 'SKILL.md' in prompt\n"
                "if 'Output JSON Schema:' in prompt:\n"
                "    assert config['permission']['*'] == 'deny'\n"
                f'    response = {json.dumps(script_fixture())!r}\n'
                'else:\n'
                "    assert config['permission']['bash'] == 'allow'\n"
                "    assert config['permission']['task'] == 'deny'\n"
                "    assert config['permission']['edit'][os.getcwd() + '/**'] == 'allow'\n"
                "    response = 'Completed silent rendering.'\n"
                "print(json.dumps({'type': 'text', 'part': {'id': 'part-1', 'messageID': 'message-1', 'text': response}}))\n",
                encoding='utf-8',
            )
            executable.chmod(0o755)
            config = replace(config_fixture(root), harness='opencode', opencode=executable)
            # Force an inherited PWD that differs from every executor directory.
            with patch.dict(os.environ, {'PWD': '/stale-parent-directory', 'OPENCODE_CONFIG_CONTENT': '{}'}):
                agent = OpenCodeAgent(executable=executable, repo_root=REPO, project_root=root,
                                      model=None, reasoning_effort='medium', verbose=False)
                value, _ = agent.run(stage='write-script', skill='write-script', schema='script', prompt='Write.')
                self.assertEqual(value, script_fixture())
                for adapter, stage in [(ProductionAgent, 'produce-video-01-of-04'),
                                       (PostProductionAgent, 'post-production')]:
                    output = root / stage
                    output.mkdir()
                    adapter(config, root)._execute(stage, root / 'request.json', output)
                    response = output / ('agent-response.txt' if stage == 'post-production'
                                         else f'{stage}.agent-response.txt')
                    self.assertEqual(response.read_text(), 'Completed silent rendering.\n')

    @patch('obscript.production.ensure_runtime')
    def test_render_and_post_production_use_the_same_native_adapter(self, ensure_runtime):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            config = replace(config_fixture(root), harness='opencode', opencode=Path('/custom/opencode'))
            for adapter, stage in [(ProductionAgent, 'produce-video'), (PostProductionAgent, 'post-production')]:
                with self.subTest(stage=stage):
                    output = root / stage
                    output.mkdir()
                    agent = adapter(config, root)
                    stream = text_event('Completed silent rendering.')
                    with patch('obscript.production.subprocess.run', return_value=
                               subprocess.CompletedProcess([], 0, stream, '')) as run:
                        agent._execute(stage, root / 'request.json', output)
                    call = run.call_args
                    command = call.args[0]
                    self.assertEqual(command[0], '/custom/opencode')
                    self.assertEqual(call.kwargs['cwd'], output)
                    self.assertEqual(call.kwargs['env']['PWD'], str(output.resolve()))
                    self.assertIn('--standalone', command)
                    self.assertNotIn('--dir', command)
                    self.assertNotIn('--variant', command)
                    self.assertNotIn('--model', command)
                    permission = json.loads(call.kwargs['env']['OPENCODE_CONFIG_CONTENT'])['permission']
                    self.assertEqual(permission['edit'], {'*': 'deny', str(output / '**'): 'allow'})
                    self.assertEqual(permission['bash'], 'allow')
                    self.assertEqual(permission['task'], 'deny')
                    self.assertIn('$hyperframes', call.kwargs['input'])
                    self.assertIn('obscript-hyperframes', call.kwargs['input'])
                    self.assertIn('Never generate', call.kwargs['input'])
                    self.assertEqual((output / 'agent-response.txt').read_text(), 'Completed silent rendering.\n')
                    self.assertTrue((output / 'executor.log').exists())
                    with patch('obscript.production.subprocess.run', return_value=
                               subprocess.CompletedProcess([], 0, json.dumps({'type': 'error', 'error': 'failed'}), '')):
                        with self.assertRaisesRegex(ProductionError, 'reported an error'):
                            agent._execute(stage, root / 'request.json', output)

    def test_runtime_config_preserves_model_provider_and_existing_skills(self):
        configured = {'model': 'provider/default', 'provider': {'provider': {'options': {}}},
                      'skills': {'paths': ['/existing/skills']}, 'permission': {'webfetch': 'deny'}}
        harness = OpenCodeHarness(Path('opencode'), REPO)
        with patch.dict(os.environ, {'OPENCODE_CONFIG_CONTENT': json.dumps(configured), 'CODEX_HOME': '/custom/codex'}):
            config = json.loads(harness.environment(output_dir=Path('/tmp/production'))['OPENCODE_CONFIG_CONTENT'])
        self.assertEqual(config['model'], configured['model'])
        self.assertEqual(config['provider'], configured['provider'])
        self.assertIn('/existing/skills', config['skills']['paths'])
        self.assertIn('/custom/codex/skills', config['skills']['paths'])
        self.assertEqual(config['permission']['webfetch'], 'deny')

    def test_invalid_inline_configuration_is_actionable(self):
        harness = OpenCodeHarness(Path('opencode'), REPO)
        for value in ['invalid', '[]']:
            with patch.dict(os.environ, {'OPENCODE_CONFIG_CONTENT': value}), self.assertRaisesRegex(AgentError, 'JSON object'):
                harness.environment()
