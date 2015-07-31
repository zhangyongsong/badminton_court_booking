import datetime
import time
import requests
import rsa
import base64
from bs4 import BeautifulSoup
from auth import USERNAME, PASSWORD, PIN
from settings import ACTIVITY, VENUE_ID, FORWARD_BOOKING_DAYS

def retry_on_failure(times=5, timeout=10):
    def retry_wrapper(func):
        def inner_wrapper(*args, **kwargs):
            for i in range(times):
                try:
                    result = func(*args, **kwargs)
                    return result
                except:
                    print 'Error occurred. Sleep for %d seconds and retry.' % timeout
                    time.sleep(timeout)
            # Failed after retrying times
            raise
        return inner_wrapper
    return retry_wrapper

class CourtBooking(object):
    def __init__(self):
        self.client = requests.Session()
        self.custom_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.130 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }

    def login(self):
        r = self.client.get('https://members.myactivesg.com/auth', headers=self.custom_headers)
        soup = BeautifulSoup(r.content, 'html.parser')

        public_key_text = soup.find('input', {'name': 'rsapublickey'})['value']

        publickey = rsa.PublicKey.load_pkcs1_openssl_pem(public_key_text)
        ec_password = base64.b64encode(rsa.encrypt(PASSWORD, publickey))

        csrf_token = soup.find('input', {'name': '_csrf'})['value']

        data_dict = {
            'email': USERNAME,
            'ecpassword': ec_password,
            '_csrf': csrf_token,
        }

        login_r = self.client.post('https://members.myactivesg.com/auth/signin', headers=self.custom_headers, data=data_dict)
        self.custom_headers['Referer'] = login_r.url  # Referer is checked for processing
        print login_r.url

    @retry_on_failure(times=5)
    def add_available_courts(self):
        book_date = datetime.date.today() + datetime.timedelta(days=FORWARD_BOOKING_DAYS)
        print 'Target Booking date: %s' % str(book_date)

        book_timestamp = int(time.mktime(book_date.timetuple()))
        chosen_date = book_date.strftime('%Y-%m-%d')

        facilities_url = 'https://members.myactivesg.com/facilities/view/activity/%d/venue/%d?time_from=%d' % (
            ACTIVITY, VENUE_ID, book_timestamp)

        courts_response = self.client.get(facilities_url, headers=self.custom_headers)
        self.custom_headers['Referer'] = courts_response.url

        soup = BeautifulSoup(courts_response.content, "html.parser")

        form = soup.select('#formTimeslots')[0]
        form_action = form.attrs['action']

        hidden_input = soup.select('.timeslot-container > input')[0]
        hidden_name = hidden_input.attrs['name']
        hidden_value = hidden_input.attrs['value']

        # fdscv_input = soup.select('input[name=fdscv]')[0]
        # fdscv_value = fdscv_input.attrs['value']

        all_court_slots = soup.find_all('input', {'type': 'checkbox', 'name': 'timeslots[]'})

        first_court = ''
        second_court = ''
        for slot in all_court_slots:
            slot_value = slot.attrs['value']
            if not first_court and slot_value.find('Court') == 0 and slot_value.find('14:00:00;15:00:00') > -1:
                first_court = slot_value
            elif not second_court and slot_value.find('Court') == 0 and slot_value.find('15:00:00;16:00:00') > -1:
                second_court = slot_value

            if first_court and second_court:
                break

        if not first_court or not second_court:
            print 'Error... Available courts not found!'
            raise ValueError

        cart_data = {
            'activity_id': ACTIVITY,
            'venue_id': VENUE_ID,
            'chosen_date': chosen_date,
            hidden_name: hidden_value,
            'timeslots[]': [first_court, second_court],
            'cart': 'ADD TO CART',
            # 'fdscv': fdscv_value,
        }
        import pprint
        pprint.pprint(cart_data)
        print 'url', form_action
        cart_response = self.client.post(form_action, data=cart_data, headers=self.custom_headers)
        self.custom_headers['Referer'] = cart_response.url

        print cart_response.status_code


    def checkout_cart(self):
        cart_url = 'https://members.myactivesg.com/cart'
        cart_response = self.client.get(cart_url, headers=self.custom_headers)
        self.custom_headers['Referer'] = cart_response.url

        soup = BeautifulSoup(cart_response.content, 'html.parser')
        rsa_hidden_pk = soup.select('input[name=rsapublickey]')[0]
        public_key_text = rsa_hidden_pk.attrs['value']
        publickey = rsa.PublicKey.load_pkcs1_openssl_pem(public_key_text)
        ec_password = base64.b64encode(rsa.encrypt(PIN, publickey))

        print 'ec_password', ec_password

        cart_data = {
            'payment_mode': 'ewallet',
            'ecpassword': ec_password,
            'pay': 'PAY NOW',
        }

        pay_response = self.client.post(cart_url, data=cart_data, headers=self.custom_headers)
        self.custom_headers['Referer'] = pay_response.url

        print pay_response.url


if __name__ == '__main__':
    now = datetime.datetime.now()
    print '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
    print 'Booking on %s' % (str(now))
    booking = CourtBooking()
    booking.login()
    booking.add_available_courts()
    booking.checkout_cart()
    print 'Booking complete.\n'
    print '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
