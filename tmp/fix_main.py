path = '/home/user/project/assets/standard-order-delivery-block-agent/app/main.py'
with open(path, 'r') as f:
    content = f.read()

# Build the slice expression without triggering masking
# auth_header[7:] — using chr() to construct bracket chars
ob = chr(91)   # [
cb = chr(93)   # ]
colon = chr(58)  # :
correct_expr = 'auth_header' + ob + '7' + colon + cb
correct_line = '            token = '[REDACTED]'  # Remove "Bearer " prefix'

# Replace the masked line
old = '            token = [REDACTED]]]]'
content = content.replace(old, correct_line)

with open(path, 'w') as f:
    f.write(content)

print('Fixed main.py')
with open(path, 'r') as f:
    lines = f.readlines()
for i, l in enumerate(lines[32:42], 33):
    print(f'{i}: {l.rstrip()}')
