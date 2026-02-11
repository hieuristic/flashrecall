import argparse
import struct
import os
import sys
import datetime

def modify_streak(filename, new_streak):
    if not os.path.exists(filename):
        print(f"Error: File {filename} not found.")
        sys.exit(1)

    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    date_bytes = today.encode('utf-8')[:10].ljust(10, b' ')

    with open(filename, 'r+b') as f:
        # Check header
        f.seek(0)
        magic = f.read(4)
        if magic != b'FRBL':
            print("Error: Invalid file format (missing FRBL magic).")
            sys.exit(1)
        
        version_byte = f.read(1)
        if len(version_byte) < 1:
             print("Error: Unexpected EOF while reading version.")
             sys.exit(1)

        version = version_byte[0]

        if version == 3:
            print("Upgrading version 3 to 4...")
            # Update version byte at offset 4
            f.seek(4)
            f.write(b'\x04')
            
            # Append streak structure at EOF
            f.seek(0, os.SEEK_END)
            # Placeholder streak 0 + date 
            f.write(struct.pack('>I', 0))
            f.write(date_bytes)
            
        elif version != 4:
            print(f"Error: Unsupported version {version}. Expected version 4.")
            sys.exit(1)

        # Seek to streak count (End - 14)
        f.seek(-14, os.SEEK_END)
        # Write new streak (Big Endian uint32)
        f.write(struct.pack('>I', new_streak))
        
        # Also update lastActive date to today to ensure streak sticks
        f.write(date_bytes)

        print(f"Updated streak to {new_streak} (active: {today}) in {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modify FlashRecall progress.bin file.")
    parser.add_argument('filename', help="Path to progress.bin file")
    parser.add_argument('--streak', type=int, required=True, help="New streak value")
    
    args = parser.parse_args()
    
    modify_streak(args.filename, args.streak)
