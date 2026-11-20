"""Offline conversation tests; no real API requests."""
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import cli
import server


def reply(action='assessment', urgent=False):
    return {'action':action, 'reply':'That could fit irritation, but the cause is still uncertain.', 'urgent':urgent}


class ConversationTests(unittest.TestCase):
    config = {'api_key':'test-key', 'model':'test-model'}

    def test_chat_continues_past_ten_turns_and_assessments(self):
        calls=[]
        def turn(messages, config, requested):
            calls.append(copy.deepcopy(messages))
            return reply()
        output=io.StringIO()
        with patch('cli.interview_turn',side_effect=turn), patch('builtins.input',side_effect=['cough']*15+['/quit']), patch('sys.stdout',output):
            cli.consultation(self.config)
        self.assertEqual(len(calls),15)
        self.assertEqual(sum(m['role']=='user' for m in calls[-1]),15)
        self.assertEqual(calls[-1][-2]['content'],reply()['reply'])
        self.assertNotIn('Question limit',output.getvalue())

    def test_assess_does_not_end_chat(self):
        with patch('cli.interview_turn',return_value=reply()) as mock, patch('builtins.input',side_effect=['cough','/assess','Could this be allergies?','/quit']), patch('sys.stdout',io.StringIO()):
            cli.consultation(self.config)
        self.assertEqual(mock.call_count,3)
        self.assertTrue(mock.call_args_list[1].args[2])
        self.assertFalse(mock.call_args_list[2].args[2])

    def test_patient_can_accept_booking_offer_without_sending_booking_to_model(self):
        answers = ['cough', 'yes', '1', '1', 'yes', 'Another question', '/quit']
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as folder:
            roster = Path(folder) / 'roster.csv'
            roster.write_text('name,weekdays,start,end\nDr. Test,1|2|3|4|5|6|7,09:00,10:00\n',
                              encoding='utf-8')
            with patch('cli.interview_turn', return_value=reply()) as model, \
                    patch('builtins.input', side_effect=answers), patch('sys.stdout', output):
                cli.consultation(self.config, roster, Path(folder) / 'appointments.sqlite3')
        self.assertIn('Would you like to book', output.getvalue())
        self.assertIn('Appointment booked. Confirmation #1.', output.getvalue())
        self.assertEqual(model.call_count, 2)
        self.assertEqual([message['content'] for message in model.call_args.args[0]
                          if message['role'] == 'user'], ['cough', 'Another question'])

    def test_urgent_advice_is_visible(self):
        output=io.StringIO()
        with patch('cli.interview_turn',return_value=reply(urgent=True)), patch('builtins.input',side_effect=['chest pain','/quit']), patch('sys.stdout',output):
            cli.consultation(self.config)
        self.assertIn('URGENT:',output.getvalue())

    def test_error_does_not_end_chat_or_save_failed_message(self):
        with patch('cli.interview_turn',side_effect=[server.LLMError('Connection failed'),reply()]) as mock, patch('builtins.input',side_effect=['failed symptom','n','new symptom','/quit']), patch('sys.stdout',io.StringIO()):
            cli.consultation(self.config)
        self.assertEqual(mock.call_count,2)
        self.assertNotIn('failed symptom',[m['content'] for m in mock.call_args.args[0]])

    def test_valid_replies_are_not_rejected_by_readiness_or_punctuation(self):
        self.assertEqual(server.validate_result(reply()),reply())
        result=reply('question')
        result['reply']='That may be irritation. Tell me a little more about when it happens.'
        self.assertEqual(server.validate_result(result),result)
        result['reply']=''
        with self.assertRaises(server.LLMError):
            server.validate_result(result)

    def test_payload_has_no_question_cap(self):
        response=io.StringIO(json.dumps({'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(reply())}]}]}))
        with patch('server.urlopen',return_value=response) as mock:
            server.interview_turn([{'role':'user','content':'cough'}],self.config,True)
        payload=json.loads(mock.call_args.args[0].data)
        self.assertFalse(payload['store'])
        self.assertIn('"assessment_requested": true',payload['instructions'])
        self.assertNotIn('question_limit',payload['instructions'])
        self.assertNotIn('enough_information',payload['text']['format']['schema']['properties'])

    def test_api_errors_do_not_leak_secrets(self):
        with patch('server.urlopen',side_effect=HTTPError('https://api.openai.com',401,'secret',{},None)):
            with self.assertRaises(server.LLMError) as caught:
                server.interview_turn([],self.config)
        self.assertEqual(str(caught.exception),'Invalid API key.')

    def test_old_config_is_compatible(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'config.json'
            path.write_text(json.dumps({**self.config,'max_questions':10}),encoding='utf-8')
            self.assertEqual(server.load_config(path),self.config)


if __name__ == '__main__':
    unittest.main()
