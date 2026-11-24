from getpass import getpass
import os
from pathlib import Path
from backend.database.connection import connect
from backend.services.auth_service import PH, normalize_email, valid_email, validate_password

def main():
    email=normalize_email(input('Local account email: '))
    if not valid_email(email): raise SystemExit('Invalid email address.')
    password=getpass('New password (12+ characters): '); validate_password(password)
    confirm=getpass('Confirm password: ')
    if password!=confirm: raise SystemExit('Passwords did not match.')
    hashed=PH.hash(password)
    c=connect()
    try:
        with c:
            row=c.execute('SELECT id FROM auth_owner WHERE id=1 AND email=?',(email,)).fetchone()
            if not row: raise SystemExit('No matching local owner account.')
            c.execute('UPDATE auth_owner SET password_hash=?,updated=strftime("%s","now") WHERE id=1',(hashed,))
            c.execute('DELETE FROM auth_sessions');c.execute('DELETE FROM auth_reset_tokens')
    finally:c.close()
    print('Local password updated. Existing sessions were signed out.')
if __name__=='__main__':main()
