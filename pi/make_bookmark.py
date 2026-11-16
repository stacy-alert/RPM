#!/usr/bin/env python3
"""One-time: create the upload token and print the "Send dogs" bookmark.

Run on the same computer where cac_fetch.py --setup was done. It makes a
random token, stores it in the private FTP folder (where upload.php reads
it), and prints the bookmark code with that token inside. Treat the
printed bookmark like a password: anyone who has it can replace the dog
list.
"""
import io
import secrets
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cac_fetch
from ftplib import error_perm

UPLOAD_URL = "https://rpmhabitatconservation.org/topsecretproject/upload.php"

JS = """javascript:(()=>{const c=x=>x?x[0].toUpperCase()+x.slice(1):null,S={s:'Small',m:'Medium',l:'Large',xl:'Extra Large'};if(location.hostname.indexOf('cincinnatianimalcare.org')<0){alert('Open the Cincinnati Animal CARE adoptable dogs page first, scroll to the bottom, then tap this.');return}const dogs=[...document.querySelectorAll('.pmp-search-result-container')].filter(e=>e.dataset.species=='dog'&&e.dataset.status=='available'&&(e.dataset.id||e.dataset.animalId)).map(e=>{const d=e.dataset,a=e.querySelector('.pmp-search-result-name-link'),p=[];['photourl','photourl1','photourl2','photourl3','photourl4'].forEach(k=>{if(d[k]&&p.indexOf(d[k])<0)p.push(d[k])});return{cac_id:d.id||d.animalId,shelter_seq_id:d.seqid||null,name:d.animalName||d.name||null,listing_url:a?a.href:null,photo_urls:p,sex:c(d.gender),age:c(d.afage),size:S[d.afsize]||d.afsize||null,date_listed:d.intakedate||null}});const ce=document.querySelector('.pmp-search-profile-count'),m=ce&&ce.textContent.match(/(\\d+)/);const f=document.createElement('form');f.method='POST';f.action='__URL__';f.target='_blank';const add=(n,v)=>{const i=document.createElement('input');i.type='hidden';i.name=n;i.value=v;f.appendChild(i)};add('token','__TOKEN__');add('data',JSON.stringify({claimed_total:m?parseInt(m[1]):null,dogs}));document.body.appendChild(f);f.submit();f.remove()})();"""


def main():
    env = cac_fetch.load_env()
    token = secrets.token_urlsafe(32)
    ftps = cac_fetch.connect(env)
    try:
        try:
            ftps.cwd(cac_fetch.PRIVATE_DIR)
        except error_perm:
            pass
        where = ftps.pwd()
        if "public_html" in where.lower():
            sys.exit(f"REFUSING: '{where}' is inside the public web folder.")
        ftps.storbinary("STOR upload_token.txt", io.BytesIO(token.encode()))
    finally:
        ftps.quit()
    print("Token saved to the private folder.\n")
    print("Copy EVERYTHING between the lines below. That is your bookmark:\n")
    print("-" * 60)
    print(JS.replace("__URL__", UPLOAD_URL).replace("__TOKEN__", token))
    print("-" * 60)


if __name__ == "__main__":
    main()
