"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"
HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
        # Disable forced https for testing
        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...
    def test_read_an_account(self):
        """Test for getting a single Account"""
        # Create one Account - _create_accounts return a list, extract the first item
        account = self._create_accounts(1)[0]
        # Make a GET request to the endpoint passing in the account ID
        resp = self.client.get(
            f"{BASE_URL}/{account.id}", content_type="application/json"
        )
        # Assert that the returned status code is 200 OK
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Get the data returned
        data = resp.get_json()
        # Assert that the 'name' attributes are matching
        self.assertEqual(data['name'], account.name)

    # To maintain code coverage - test sad paths as well, e.g.: read an account with
    # an account id that does not exists
    def test_get_account_not_found(self):
        """Test for getting an Account that does not exists"""
        # Make a GET request to the endpoint passing in an ID that does not belong to
        # an account
        resp = self.client.get(f'{BASE_URL}/0')
        # Assert that the returned status code was 404
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_account_list(self):
        """Test for listing accounts"""
        # Create 5 accounts
        self._create_accounts(5)
        # Send a GET request to the endpoint to query all accounts
        resp = self.client.get(BASE_URL)
        # Assert that the status code is 200 - OK
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Get the data from the response object
        data = resp.get_json()
        # Assert that the length of the returned object is 5
        self.assertEqual(len(data), 5)

    def test_update_account(self):
        """Test for updating an existing account"""
        # Create an account to update using AccountFactory
        account = AccountFactory()
        # Send a POST request to the endpoint to create the new account object
        resp = self.client.post(BASE_URL, json=account.serialize())
        # Assert that the response status code from POST is 201 - CREATED
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Make an update to the account
        # Get the data from the POST response object
        data = resp.get_json()
        # Change the account name to a dummy value
        data['name'] = 'something known'
        # Send a PUT request to update the account in the db
        resp = self.client.put(f'{BASE_URL}/{data["id"]}', json=data)
        # Assert that the response status code is 200 - OK
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Get the data from the PUT response object
        data = resp.get_json()
        # Assert that the name for tha account has been changed
        self.assertEqual(data['name'], 'something known')

    def test_put_account_not_found(self):
        """Test for updating an account that does not exist"""
        # Make a PUT request to the endpoint passing in an ID that does not belong to
        # an account
        resp = self.client.put(f'{BASE_URL}/0')
        # Assert that the returned status code was 404
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_account(self):
        """Test to delete an account"""
        # Create an account that will be deleted
        account = self._create_accounts(1)[0]
        # Send a DELETE request to the endpoint passing in the id of the account to be
        # deleted
        resp = self.client.delete(f'{BASE_URL}/{account.id}')
        # Asser that the response status code is 204 - NO CONTENT
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_account_not_found(self):
        """Test for deleting an account that does not exist"""
        # Make a DELETE request to the endpoint passing in an ID that does not belong to
        # an account
        resp = self.client.delete(f'{BASE_URL}/0')
        # Assert that the returned status code was 404
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_method_not_allowed(self):
        """Test for illegal method call"""
        # Send a DELETE request to an endpoint that does not support that HTTP method
        resp = self.client.delete(BASE_URL)
        # Assert that the response status code is 405 - METHOD NOT ALLOWED
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # SECURITY HEADERS
    def test_security_headers(self):
        """Test to assert the presence of security headers"""
        # Call root URL, passing in HTTPS_ENVIRON
        resp = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        # Assert response status code 200 - OK
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        # Assert that each response header matches the expected header from above
        for k, v in headers.items():
            self.assertEqual(resp.headers.get(k), v)

    # CORS POLICIES
    def test_cors_security(self):
        """Test to assert the presence of CORS header"""
        resp = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        # Assert response status code 200 - OK
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Assert the presence of CORS header
        self.assertEqual(resp.headers.get('Access-Control-Allow-Origin'), '*')
