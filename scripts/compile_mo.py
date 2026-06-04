"""Compile .po to .mo files manually."""
import os, struct

def write_mo(po_path, mo_path):
    with open(po_path, 'r', encoding='utf-8') as f:
        content = f.read()

    translations = {}
    current_id = None
    current_str = None
    in_id = False
    in_str = False

    for line in content.split('\n'):
        line_stripped = line.strip()
        if line_stripped.startswith('msgid ') or line_stripped.startswith('msgid_'):
            if current_id is not None and current_str is not None:
                translations[current_id] = current_str
            # parse msgid "..."
            if '"' in line_stripped:
                start = line_stripped.index('"') + 1
                end = line_stripped.rindex('"')
                current_id = line_stripped[start:end]
            else:
                current_id = ''
            in_id = True
            in_str = False
            current_str = None
        elif line_stripped.startswith('msgstr '):
            if '"' in line_stripped:
                start = line_stripped.index('"') + 1
                end = line_stripped.rindex('"')
                current_str = line_stripped[start:end]
            else:
                current_str = ''
            in_id = False
            in_str = True
        elif in_id and line_stripped.startswith('"'):
            end = line_stripped.rindex('"')
            current_id += line_stripped[1:end]
        elif in_str and line_stripped.startswith('"'):
            end = line_stripped.rindex('"')
            current_str += line_stripped[1:end]

    if current_id is not None and current_str is not None:
        translations[current_id] = current_str

    msgids = list(translations.keys())
    msgstrs = [translations[k] for k in msgids]
    num = len(msgids)

    # Build offsets
    header_size = 112  # fixed header
    orig_table_offset = header_size
    trans_table_offset = orig_table_offset + 8 * num
    orig_strings_offset = trans_table_offset + 8 * num
    trans_strings_offset = orig_strings_offset

    for mid in msgids:
        trans_strings_offset += len(mid.encode('utf-8')) + 1

    data = struct.pack('<IIIIII', 0x950412de, 0, num, orig_table_offset, trans_table_offset, orig_strings_offset)

    # Original strings table: length + offset
    current_offset = orig_strings_offset
    for mid in msgids:
        encoded = mid.encode('utf-8')
        data += struct.pack('<II', len(encoded), current_offset)
        current_offset += len(encoded) + 1

    # Translated strings table: length + offset
    current_offset = trans_strings_offset
    for mstr in msgstrs:
        encoded = mstr.encode('utf-8')
        data += struct.pack('<II', len(encoded), current_offset)
        current_offset += len(encoded) + 1

    for mid in msgids:
        data += mid.encode('utf-8') + b'\x00'
    for mstr in msgstrs:
        data += mstr.encode('utf-8') + b'\x00'

    os.makedirs(os.path.dirname(mo_path), exist_ok=True)
    with open(mo_path, 'wb') as f:
        f.write(data)

write_mo('locale/en/LC_MESSAGES/django.po', 'locale/en/LC_MESSAGES/django.mo')
write_mo('locale/fr/LC_MESSAGES/django.po', 'locale/fr/LC_MESSAGES/django.mo')
print('.mo files created successfully')
