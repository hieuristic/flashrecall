import argparse
import struct
import os
import sys
import datetime

def modify_streak(filename, new_dates, recalculate_streak):
    if not os.path.exists(filename):
        print(f"Error: File {filename} not found.")
        sys.exit(1)

    today_dt = datetime.datetime.utcnow()
    today_str = today_dt.strftime('%Y-%m-%d')
    date_bytes_today = today_str.encode('utf-8')[:10].ljust(10, b' ')

    with open(filename, 'rb') as f:
        data = bytearray(f.read())

    # Check header
    if data[:4] != b'FRBL':
        print("Error: Invalid file format (missing FRBL magic).")
        sys.exit(1)
        
    version = data[4]

    if version == 3:
        print("Upgrading version 3 to 4...")
        data[4] = 4
        # Append streak structure at EOF
        data.extend(struct.pack('>I', 0))
        data.extend(date_bytes_today)
    elif version != 4:
        print(f"Error: Unsupported version {version}. Expected version 4.")
        sys.exit(1)
        
    hcount = struct.unpack('>I', data[10:14])[0]
    
    # Parse history
    history = {}
    hdata = data[14:14+hcount*18]
    for i in range(hcount):
        entry = hdata[i*18:(i+1)*18]
        date_str = entry[:10].decode('utf-8').strip()
        learned, reviewed = struct.unpack('>II', entry[10:18])
        history[date_str] = {'learned': learned, 'reviewed': reviewed}

    # Add new dates
    if new_dates:
        for d in new_dates:
            days_ago = int(d[0])
            learned = int(d[1])
            practiced = int(d[2])
            target_date = (today_dt - datetime.timedelta(days=days_ago)).strftime('%Y-%m-%d')
            history[target_date] = {'learned': learned, 'reviewed': practiced}
            print(f"Added/Updated history for {target_date}: learned={learned}, practiced={practiced}")

    # Re-pack history
    # Sort history chronologically
    sorted_dates = sorted(history.keys())
    
    new_hcount = len(sorted_dates)
    new_hdata = bytearray()
    for d in sorted_dates:
        d_bytes = d.encode('utf-8')[:10].ljust(10, b' ')
        new_hdata.extend(d_bytes)
        new_hdata.extend(struct.pack('>II', history[d]['learned'], history[d]['reviewed']))

    rest = data[14+hcount*18:]
    
    # Recalculate streak if needed
    if recalculate_streak:
        streak = 0
        last_active = None
        
        current_date = today_dt
        
        # Check today
        t_str = current_date.strftime("%Y-%m-%d")
        if t_str in history and (history[t_str]['learned'] > 0 or history[t_str]['reviewed'] > 0):
            streak += 1
            last_active = t_str
            current_date -= datetime.timedelta(days=1)
        else:
            # Check yesterday
            yesterday_dt = current_date - datetime.timedelta(days=1)
            y_str = yesterday_dt.strftime("%Y-%m-%d")
            if y_str in history and (history[y_str]['learned'] > 0 or history[y_str]['reviewed'] > 0):
                last_active = y_str
                current_date = yesterday_dt
            else:
                last_active = t_str
                
        # Keep going backwards
        if last_active and last_active != t_str or (last_active == t_str and streak > 0):
            while True:
                prev_str = current_date.strftime("%Y-%m-%d")
                if prev_str in history and (history[prev_str]['learned'] > 0 or history[prev_str]['reviewed'] > 0):
                    if streak == 0:
                        pass # already handled the first one
                    streak += 1
                    if not last_active:
                        last_active = prev_str
                    current_date -= datetime.timedelta(days=1)
                else:
                    break
        
        if not last_active:
            last_active = today_str
            
        print(f"Calculated new streak: {streak}, lastActive: {last_active}")
        
        # update rest (last 14 bytes)
        date_bytes = last_active.encode('utf-8')[:10].ljust(10, b' ')
        rest = rest[:-14] + struct.pack('>I', streak) + date_bytes

    # Write back
    with open(filename, 'wb') as f:
        f.write(data[:10])
        f.write(struct.pack('>I', new_hcount))
        f.write(new_hdata)
        f.write(rest)
        
    print(f"Successfully updated {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modify FlashRecall progress.bin file.")
    parser.add_argument('filename', help="Path to progress.bin file")
    parser.add_argument('--streak', action='store_true', help="Recalculate streak based on history")
    parser.add_argument('--date', action='append', nargs=3, metavar=('DAYS_AGO', 'LEARNED', 'PRACTICED'), help="Add/update history for a given day offset")
    
    args = parser.parse_args()
    
    modify_streak(args.filename, args.date, args.streak)
