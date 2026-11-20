"""Run an open-ended English terminal conversation: python cli.py."""
from server import LLMError, interview_turn, load_config


def patient_input(prompt):
    while True:
        answer = input(prompt).strip()
        if answer.lower() in ('/quit', '/assess'):
            return answer.lower()
        if 1 <= len(answer) <= 4000:
            return answer
        print('Please enter 1 to 4000 characters, /assess or /quit.')


def consultation(config):
    print('MEDICAL ARRANGEMENT | LLM Chat')
    print(f"Model: {config['model']}")
    print('This is preliminary guidance, not a diagnosis. Seek emergency care for urgent symptoms.')
    print('Your answers are sent to OpenAI. Do not include identifying information.')
    print('Keep chatting for as long as you need. Type /assess for an impression, or /quit to exit.')
    opening = "Hi, I'm here to help you think through what's going on. What's been bothering you?"
    print('\nAssistant: ' + opening)
    messages = [{'role':'assistant', 'content':opening}]
    while True:
        answer = patient_input('You: ')
        if answer == '/quit':
            print('Goodbye.')
            return
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
            print('URGENT: Seek local emergency care immediately. Do not wait for this chat.')
        messages = pending + [{'role':'assistant', 'content':result['reply']}]


def main():
    try:
        consultation(load_config())
    except LLMError as error:
        print('Configuration error: ' + str(error))
        return 1
    except (KeyboardInterrupt, EOFError):
        print('\nConversation ended.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
