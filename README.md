# asn-from-barcode
Parse ASN from barcode in consumed documents as a post-consume script in paperless-ng

## Installation and configuration

Install requirements for python packages: pdftoppm is contained in poppler-utils, zbarimg is contained in libzbar0

For ubuntu, you may use:

`apt install poppler-utils libzbar0`

Install python packages used: pyzbar to parse the barcodes, pdf2image to convert the pdf to png beforehand, psycopg to access the database of paperless-ng 

`pip install pyzbar pdf2image psycopg[binary]`

Place the script in some meaningful folder, e.g., `/opt/paperless-ng/scripts/parse-asn-for-paperless.py`

Make sure that paperless ng has read and execute permissions on the file, e.g.:

`chown paperlessng /opt/paperless-ng/scripts/parse-asn-for-paperless.py && chmod 750 /opt/paperless-ng/scripts/parse-asn-for-paperless.py`

Configure paperless-ng to execute the script, e.g., by setting `PAPERLESS_POST_CONSUME_SCRIPT=/opt/paperless-ng/scripts/parse-asn-for-paperless.py` in `/etc/paperless.conf` or where you configure your paperless instance.

If you want to use the logging of the script, either adjust the log file configured or create the directory `/var/log/paperless` and make it accessible to the paperless-ng user.

Fine tune the code to your needs, e.g., by adjusting the relevant code types (CODE128 by default). The valid values depend on zbar, e.g., see [this list](https://github.com/NaturalHistoryMuseum/pyzbar/blob/76d337d8f41a45aa24dc16e103dc2ea446e6da8a/pyzbar/wrapper.py#L46-L64).
