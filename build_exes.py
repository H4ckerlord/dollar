import os

# Configuration for each person
people = [
    {'name': '1', 'group_id': '-1003587821331'},  # Replace with actual group IDs
    {'name': '2', 'group_id': 'GROUP_ID_2'},
    {'name': '3', 'group_id': 'GROUP_ID_3'},
    {'name': '4', 'group_id': 'GROUP_ID_4'},
    {'name': '5', 'group_id': 'GROUP_ID_5'},
]

# Read the template
with open('client_template.py', 'r') as f:
    template = f.read()

# Create a .py file for each person
for person in people:
    modified = template.replace('EXE_NAME = "1"', f'EXE_NAME = "{person["name"]}"')
    modified = modified.replace('GROUP_ID = "YOUR_GROUP_ID_HERE"', f'GROUP_ID = "{person["group_id"]}"')
    
    filename = f'client_{person["name"]}.py'
    with open(filename, 'w') as f:
        f.write(modified)
    print(f"[+] Created {filename}")

print("\n[+] Run these commands to build SILENT .exe files:")
for person in people:
    print(f'pyinstaller --onefile --noconsole --name "{person["name"]}" client_{person["name"]}.py')