with open('frontend/src/App.test.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("expect(screen.getByText('RUN: run-123'))", "expect(screen.getByText('run-123'))")

with open('frontend/src/App.test.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
