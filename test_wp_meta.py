#!/usr/bin/env python3
"""Test rápido del endpoint GET de meta."""
import requests

URL = 'https://inmobi.com.ec/'
USER = 'daniareyes.ab@gmail.com'
PWD = 'LTdh AdGN x6Mf J8Px nsk2 GB7z'
POST_ID = 27588

print("=== Test endpoint odoo-houzez/v1/meta (GET) ===")
try:
    resp = requests.get(
        f'{URL}wp-json/odoo-houzez/v1/meta/{POST_ID}',
        auth=(USER, PWD), timeout=15)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        d = resp.json()
        print(f"✅ {len(d)} campos recibidos!")
        for k in ['fave_property_price', 'fave_property_size', 'fave_property_land',
                   'fave_property_bedrooms', 'fave_property_bathrooms', 'fave_property_garage',
                   'fave_property_address', 'houzez_geolocation_lat', 'houzez_geolocation_long']:
            print(f"  {k} = {d.get(k, 'NOT FOUND')}")
    else:
        print(f"❌ {resp.text[:300]}")
except Exception as e:
    print(f"❌ Error: {e}")
