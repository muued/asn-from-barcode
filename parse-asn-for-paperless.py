#!/usr/bin/env python3

# This script was heavily inspired by https://github.com/jonaswinkler/paperless-ng/files/6563231/asn.py.zip posted by https://github.com/andbez in https://github.com/jonaswinkler/paperless-ng/discussions/460


from pdf2image import convert_from_path

from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError
)

from pyzbar.pyzbar import decode
from PIL import Image

import tempfile
from operator import itemgetter

import os
import sys
import psycopg
from typing import Optional

import logging

logging.basicConfig(filename='/var/log/paperless/post-consumption.log', level=logging.DEBUG)

RELEVANT_CODE_TYPES = ['CODE128']
SANITY_CHECK_THRESHOLD = 50

# Declare necessary variables
DOCUMENT = {}
ASN = {}

# Get Arguments and put it into readable vars
DOCUMENT['ID'] = sys.argv[1]
DOCUMENT['FILE_NAME'] = sys.argv[2]
DOCUMENT['SOURCE_PATH'] = sys.argv[3]
DOCUMENT['THUMBNAIL_PATH'] = sys.argv[4]
DOCUMENT['DOWNLOAD_URL'] = sys.argv[5]
DOCUMENT['THUMBNAIL_URL'] = sys.argv[6]
DOCUMENT['CORRESPONDENT'] = sys.argv[7]
DOCUMENT['TAGS'] = sys.argv[8]

logging.debug (DOCUMENT)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.getenv('PAPERLESS_DATA_DIR', os.path.join(BASE_DIR, "..", "data"))

# the database section was taken from
# https://github.com/jonaswinkler/paperless-ng/blob/7bc8325df910ab57ed07849a3ce49a3011ba55b6/src/paperless/settings.py#L266-L294

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(
            DATA_DIR,
            "db.sqlite3"
        )
    }
}

if os.getenv("PAPERLESS_DBHOST"):
    # Have sqlite available as a second option for management commands
    # This is important when migrating to/from sqlite
    DATABASES['sqlite'] = DATABASES['default'].copy()

    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "HOST": os.getenv("PAPERLESS_DBHOST"),
        "NAME": os.getenv("PAPERLESS_DBNAME", "paperless"),
        "USER": os.getenv("PAPERLESS_DBUSER", "paperless"),
        "PASSWORD": os.getenv("PAPERLESS_DBPASS", "paperless"),
        'OPTIONS': {'sslmode': os.getenv("PAPERLESS_DBSSLMODE", "prefer")},
    }
    if os.getenv("PAPERLESS_DBPORT"):
        DATABASES["default"]["PORT"] = os.getenv("PAPERLESS_DBPORT")


def parseCodes(document, maxAsn: Optional[int] = None) -> Optional[int]:
    with tempfile.TemporaryDirectory() as path:
        pngs = convert_from_path(document['SOURCE_PATH'], output_folder=path, dpi=300, single_file=True)
        decodedCodes = decode(pngs[0])
        logging.debug('document %s: decoded codes: %s', document['ID'], decodedCodes)
        if (0 == len(decodedCodes)):
            logging.info('document %s: no codes found', document['ID'])
            return None
        filtered = list(filter(lambda c: c.type in RELEVANT_CODE_TYPES and c.data.isdigit(), decodedCodes))
        if (0 == len(filtered)):
            logging.info('document %s: no codes of correct type/format found', document['ID'])
            return None
        numbers = list(filter(lambda number: None == maxAsn or abs(number-maxAsn) < SANITY_CHECK_THRESHOLD, map(lambda code: int(code.data, 10), filtered)))
        if (0 == len(numbers)):
            logging.info('document %s: all found codes failed the sanity check', document['ID'])
            return None
        if (1 == len(numbers)):
            return numbers[0]

        m = maxAsn if maxAsn != None else 0
        data = map(lambda asn: (asn-m, abs(asn-m), asn), numbers)
        return sorted(sorted(data, key=itemgetter(0), reverse=True), key=itemgetter(1))[0][2]


# Connect to an existing database
with psycopg.connect(user=DATABASES['default']['USER'],
                     password=DATABASES['default']['PASSWORD'],
                     host=DATABASES['default']['HOST'],
                     port=DATABASES['default']['PORT'],
                     dbname=DATABASES['default']['NAME']) as conn:

    # Open a cursor to perform database operations
    with conn.cursor() as cur:

        maxAsnRow = cur.execute("SELECT MAX(archive_serial_number) FROM documents_document").fetchone()
        maxAsn = maxAsnRow[0] if maxAsnRow != None else None
        asn = parseCodes(DOCUMENT, maxAsn)

        if (asn == None):
            raise SystemExit()

        if (asn == maxAsn):
            logging.warning('document %s: found ASN that is already used in the database: %s', DOCUMENT['FILE_NAME'], asn)
            raise SystemExit()

        logging.info('document %s: using ASN %s', DOCUMENT['ID'], asn)

        cur.execute(
            "UPDATE public.documents_document SET archive_serial_number = %s WHERE ID = %s and archive_serial_number is null;",
            (asn, DOCUMENT['ID']))

        conn.commit()

