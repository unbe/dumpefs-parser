import fileinput
import re
import os
from recordtype import recordtype
import itertools
import binascii

Block = recordtype('Block', 'unit index ref name p misc data', default=None)

blocks = {}
boot_block = None
data_re = re.compile(r"([0-9A-F]+): (([0-9A-F]{2}( |$))+)( |$).*")
def process_block(block_text):
  global boot_block, blocks
  block = Block(misc={})
  stack = ["top"]
  for line in block_text:
    if block.unit is None:
      m = re.match(r"H\[(\w+)\] L\[(\w+)\] P\[(\w+)\]", line)
      assert m is not None
      block.unit = int(m.group(2), 16)
      block.index = int(m.group(1), 16)
      block.ref = (block.unit, block.index)
      block.p = int(m.group(3), 16)
      continue
    if line[0] == "(":
      continue
  
    if stack[0] == "data":
      if block.data is None:
        block.data = ""
      m = re.match(r"\*([0-9A-F]+)", line)
      if m:
        repeat = int(m.group(1), 16)
        block.data += last_data * (repeat - 1) 
        continue
      m = data_re.match(line)
      assert m is not None, "[%s]" % line
      offset = int(m.group(1), 16)
      assert offset == len(block.data), "%d <= %s" % (offset, str(block))
      hexdata = m.group(2).replace(" ", "")
      last_data = binascii.unhexlify(hexdata)
      block.data += last_data
      continue
      
    level = sum(1 for x in itertools.takewhile(lambda char: char == '.', line))
    while level < len(stack):
      stack.pop()
    for match in re.finditer("\\."*level + "([^=]+)(=|$)(\\S*)", line):
      value = match.group(3)
      if len(value) == 0 or value[0] == '"' and value[-1] == '"' or value[0] == "'" and value[-1] == "'":
        value = value[1:-1]
      else:
        value = int(value, 16)
      block.misc[".".join(stack + [match.group(1)])] = value
    stack.append(match.group(1))
  if "name" in block.misc:
    block.name = block.misc["name"]
  blocks[block.ref] = block
  if "boot" in block.misc:
    assert boot_block is None
    boot_block = block

def get_ref(block, prefix):
  if prefix + ".logi_unit" in block.misc:
    return (block.misc[prefix + ".logi_unit"], block.misc[prefix + ".index"])
#    return (int(block.misc[prefix + ".logi_unit"], 16), int(block.misc[prefix + ".index"], 16))
  else:
    return None

def traverse(dir_block, path, file=None):
  if file is not None:
    print "File:", path
  else:
    print "Dir:", path
    os.makedirs(path)
  if not "dirent.first" in dir_block.misc:
    return
  block = blocks[get_ref(dir_block, "dirent.first")]
  while True:
    if file is not None:
      assert block.data is not None
      file.write(block.data)
    mode = block.misc.get("stat.mode", 0)
    if mode != 0:
      name = path + "/" + block.name
    if mode & 0x4000:
      traverse(block, name)
    if mode & 0x8000:
      fp = open(name, "wb")
      traverse(block, name, fp)
      fp.close()
    next_ref = get_ref(block, "top.next")
    if next_ref:
      block = blocks[next_ref]
    else:
      return

tblock = []
for line in fileinput.input():
  if line[:78] == '-'*78 or line[:78] == '='*78:
    process_block(tblock)
    tblock=[]
  else:
    tblock.append(line.rstrip())

process_block(tblock)
assert boot_block is not None
print "Parsed %d blocks." % len(blocks)

print "Boot block:", boot_block.ref
root_block = blocks[get_ref(boot_block, "boot.root")]
print "Root block:", root_block.ref, root_block.name
traverse(root_block, "out")
