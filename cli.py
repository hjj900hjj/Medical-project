"""Run an open-ended English terminal conversation: python cli.py."""
import argparse
import sqlite3
from pathlib import Path

from scheduling import BookingAgent
from server import LLMError, ROOT, interview_turn, load_config


def patient_input(prompt):
    while True:
        answer = input(prompt).strip()
        if answer.lower() in ('/quit', '/assess', '/book'):
            return answer.lower()
        if 1 <= len(answer) <= 4000:
            return answer
        print('Please enter 1 to 4000 characters, /assess, /book or /quit.')


def consultation(config, roster_path=ROOT / 'data' / 'doctors.csv',
                 database_path=ROOT / 'appointments.sqlite3'):
    print('MEDICAL ARRANGEMENT | LLM Chat')
    print(f"Model: {config['model']}")
    print('This is preliminary guidance, not a diagnosis. Seek emergency care for urgent symptoms.')
    print('Your answers are sent to OpenAI. Do not include identifying information.')
    print('Type /assess for an impression, /book to check appointments, or /quit to exit.')
    opening = "Hi, I'm here to help you think through what's going on. What's been bothering you?"
    print('\nAssistant: ' + opening)
    messages = [{'role':'assistant', 'content':opening}]
    booking_offered = False
    automatic_offer_shown = False
    urgent_encounter = False
    while True:
        answer = patient_input('You: ')
        if answer == '/quit':
            print('Goodbye.')
            return
        if answer == '/book' or (booking_offered and answer.lower() in ('yes', 'y')):
            booking_offered = False
            if urgent_encounter:
                print('Please seek local emergency care immediately.')
                continue
            try:
                BookingAgent(roster_path, database_path).run()
            except (OSError, ValueError, sqlite3.Error) as error:
                print(f'Could not complete scheduling: {error}')
            continue
        if booking_offered and answer.lower() in ('no', 'n'):
            booking_offered = False
            continue
        booking_offered = False
        assessment_requested = answer == '/assess'
        if assessment_requested and not any(m['role'] == 'user' for m in messages):
            print('Please describe what is bothering you first.')
            continue
        content = 'What is your impression based on what I have shared so far?' if assessment_requested else answer
        pending = messages + [{'role':'user', 'content':content}]
        while True:
            print('\nThinking...')
            try:
                result = interview_turn(pending, config, assessment_requested)
                break
            except LLMError as error:
                print('Error: ' + str(error))
                if input('Retry the same request? [y/N]: ').strip().lower() != 'y':
                    print('That message was not added. You can try another message or type /quit.')
                    result = None
                    break
        if result is None:
            continue
        print('\nAssistant: ' + result['reply'].strip())
        if result['urgent']:
            urgent_encounter = True
            print('URGENT: Seek local emergency care immediately. Do not wait for this chat.')
        if not urgent_encounter and (
            assessment_requested or (result['action'] == 'assessment' and not automatic_offer_shown)
        ):
            booking_offered = True
            automatic_offer_shown = True
            print('Would you like to book an appointment? Type yes, no, or keep chatting.')
        messages = pending + [{'role':'assistant', 'content':result['reply']}]


def main():
    parser = argparse.ArgumentParser(description='Run the medical interview and appointment CLI.')
    parser.add_argument('--doctors', type=Path, default=ROOT / 'data' / 'doctors.csv',
                        help='Path to the doctor duty roster CSV.')
    args = parser.parse_args()
    try:
        consultation(load_config(), args.doctors)
    except LLMError as error:
        print('Configuration error: ' + str(error))
        return 1
    except (KeyboardInterrupt, EOFError):
        print('\nConversation ended.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
