import requests
import rsa
import base64
from bs4 import BeautifulSoup
from auth import USERNAME, PASSWORD, PIN


class CourtBooking(object):
    def __init__(self):
        self.client = requests.Session()
        self.custom_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.130 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }

    def login(self):
        r = self.client.get('https://members.myactivesg.com/auth', headers=self.custom_headers)
        soup = BeautifulSoup(r.content, 'html.parser')

        public_key_text = soup.find('input', {'name': 'rsapublickey'})['value']

        publickey = rsa.PublicKey.load_pkcs1_openssl_pem(public_key_text)
        ec_password = base64.b64encode(rsa.encrypt(PASSWORD, publickey))
        print 'encrypted password:', ec_password

        csrf_token = soup.find('input', {'name': '_csrf'})['value']
        print 'csrf_token:', csrf_token

        data_dict = {
            'email': USERNAME,
            'ecpassword': ec_password,
            '_csrf': csrf_token,
        }

        login_r = self.client.post('https://members.myactivesg.com/auth/signin', headers=self.custom_headers, data=data_dict)
        print login_r.url











if __name__ == '__main__':
    booking = CourtBooking()
    booking.login()
