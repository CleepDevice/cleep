cmds = dir('')
print(cmds)
for cmd in cmds[:]:
    print(cmd)
    if cmd.startswith('_'):
        cmds.remove(cmd)
print(cmds)
