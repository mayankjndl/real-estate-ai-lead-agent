with open('agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '"searching for", "i want a 2bhk", "i want a 3bhk", "i want a 1bhk",'
new = '''"searching for", "i want a 2bhk", "i want a 3bhk", "i want a 1bhk",
        # Location-only openers that skip "i'm looking" prefix (common in real usage):
        "looking to buy in", "looking to rent in", "looking to buy",
        "looking to rent", "want to buy in", "want to rent in",
        "buy in ", "rent in ",
        # Investment intent:
        "investment property", "invest in",'''

content = content.replace(old, new)

with open('agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open('agent.py', 'r', encoding='utf-8') as f:
    data = f.read()
print("looking to buy in:", "looking to buy in" in data)
print("investment property:", "investment property" in data)
