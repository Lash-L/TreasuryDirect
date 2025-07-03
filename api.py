"""
DISCLAIMER: THIS CODE WAS GENERATED 100% by a LLM. USE IT AT YOUR OWN RISK.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import sys


class TreasuryDirectAPI:
    """
    An asynchronous Python client for interacting with the TreasuryDirect website.
    This class supports two main functionalities:
    1. Calculating the value of a paper savings bond without authentication.
    2. A full login flow to retrieve a user's Series I Savings Bond holdings.
    """

    def __init__(self):
        self.base_url = "https://treasurydirect.gov"
        self.session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
        self.headers = {
            "Host": "treasurydirect.gov",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
            "Origin": "https://treasurydirect.gov",
        }

    async def close(self):
        """Closes the aiohttp client session."""
        await self.session.close()

    def _parse_html(self, html_content):
        """Creates a BeautifulSoup object from HTML content."""
        return BeautifulSoup(html_content, "html.parser")

    def _extract_csrf_token(self, soup):
        """Extracts the _csrf token from a BeautifulSoup object."""
        csrf_input = soup.find("input", {"name": "_csrf"})
        if not csrf_input:
            raise ValueError("CSRF token not found on the page.")
        return csrf_input["value"]

    async def get_initial_login_page(self):
        """
        # Initial Login Page
        Retrieves the initial login page to get the first _csrf token.
        """
        url = f"{self.base_url}/RS/UN-Display.do"
        headers = self.headers.copy()
        headers.update(
            {
                "Referer": f"{self.base_url}/log-in/",
                "Sec-Fetch-Site": "none",
            }
        )
        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            html = await response.text()
            soup = self._parse_html(html)
            return self._extract_csrf_token(soup)

    async def submit_username(self, username, csrf_token):
        """
        # Submit Username
        Submits the username and _csrf token.
        """
        url = f"{self.base_url}/RS/UN-Submit.do"
        headers = self.headers.copy()
        headers.update(
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"{self.base_url}/RS/UN-Display.do",
            }
        )
        payload = {"username": username, "submit": "Submit", "_csrf": csrf_token}
        async with self.session.post(url, headers=headers, data=payload) as response:
            response.raise_for_status()
            html = await response.text()
            soup = self._parse_html(html)
            # Check for login errors
            if "The Account Number you entered was not found" in html:
                raise ValueError(
                    "Login failed: The Account Number you entered was not found."
                )
            return self._extract_csrf_token(soup)

    async def submit_otp(self, otp, csrf_token):
        """
        # Submit One-Time Passcode (OTP)
        Submits the OTP. This request results in a 302 redirect.
        """
        url = f"{self.base_url}/RS/OTP-Submit.do"
        headers = self.headers.copy()
        headers.update(
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"{self.base_url}/RS/OTP-New.do",
            }
        )
        payload = {"otp": otp, "enter.x": "Submit", "_csrf": csrf_token}
        # We expect a 302 redirect, allow_redirects=False lets us inspect it,
        # but the session handles cookies correctly even with redirects enabled.
        async with self.session.post(
            url, headers=headers, data=payload, allow_redirects=True
        ) as response:
            if response.status != 200:
                # Check the final URL after redirect
                if "PW-Display.do" not in str(response.url):
                    html = await response.text()
                    if "The passcode you entered is not valid" in html:
                        raise ValueError(
                            "OTP submission failed: The passcode you entered is not valid."
                        )
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                        message="Failed to redirect to password page after OTP submission.",
                    )
            return await response.text()

    async def get_password_page(self):
        """
        # Password Entry Page
        Retrieves the password entry page to get the next _csrf token.
        """
        url = f"{self.base_url}/RS/PW-Display.do"
        headers = self.headers.copy()
        headers.update(
            {
                "Referer": f"{self.base_url}/RS/OTP-New.do",
            }
        )
        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            html = await response.text()
            soup = self._parse_html(html)
            return self._extract_csrf_token(soup)

    async def submit_password(self, password, csrf_token):
        """
        # Submit Password
        Submits the password to complete the login process.
        """
        url = f"{self.base_url}/RS/PW-Submit.do"
        headers = self.headers.copy()
        headers.update(
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"{self.base_url}/RS/PW-Display.do",
            }
        )
        payload = {"password": password, "_csrf": csrf_token, "enter.x": "Submit"}
        async with self.session.post(url, headers=headers, data=payload) as response:
            response.raise_for_status()
            html = await response.text()
            if "The password you entered is not valid" in html:
                raise ValueError("Login failed: The password you entered is not valid.")
            return html

    async def get_current_holdings(self, welcome_page_html):
        """
        # Get Current Holdings
        Parses the welcome page to find the current holdings link, then fetches that page.
        """
        soup = self._parse_html(welcome_page_html)
        holdings_link = soup.find("a", text="Current Holdings")
        if not holdings_link or not holdings_link.has_attr("href"):
            raise ValueError(
                "Could not find 'Current Holdings' link on the account summary page."
            )

        parsed_url = urlparse(holdings_link["href"])
        query_params = parse_qs(parsed_url.query)

        params_for_get = {
            "UIHandler": "ch.DisplayCurrentHoldings",
            "primary": query_params.get("primary", [None])[0],
            "processID": query_params.get("processID", [None])[0],
            "fromTabLink": "true",
            "uiFrom": "misc.DisplayWelcome",
        }

        if not all(params_for_get.values()):
            raise ValueError(
                "Could not extract necessary parameters from holdings link."
            )

        url = f"{self.base_url}/RS/RSGatewayRW"
        headers = self.headers.copy()
        # The referer is the welcome page, but it's dynamic. Let's build a plausible one.
        headers["Referer"] = f"{self.base_url}/RS/misc.DisplayWelcome"

        async with self.session.get(
            url, headers=headers, params=params_for_get
        ) as response:
            response.raise_for_status()
            html = await response.text()

            # Now, extract form data for the next step from this page
            soup = self._parse_html(html)

            # Find Series I radio button
            series_i_radio = soup.find(
                "input",
                {"name": "seriesCode", "type": "radio"},
                find_next_sibling_text="Series I Savings Bond",
            )
            if not series_i_radio:
                # Fallback search if text isn't a direct sibling
                tr = soup.find("td", text="Series I Savings Bond")
                if tr:
                    series_i_radio = tr.find_previous_sibling("td").find("input")

            if not series_i_radio:
                raise ValueError(
                    "Could not find the 'Series I Savings Bond' radio button."
                )

            series_code = series_i_radio["value"]

            # Find dynamic submit button name
            submit_button = soup.find("input", {"type": "submit", "value": "Submit"})
            if not submit_button:
                raise ValueError(
                    "Could not find the submit button on the holdings page."
                )
            submit_name = submit_button["name"]

            # Find hidden processID and primary values
            process_id = soup.find("input", {"name": "processID"})["value"]
            primary = soup.find("input", {"name": "primary"})["value"]

            return {
                "seriesCode": series_code,
                "submit_name": submit_name,
                "processID": process_id,
                "primary": primary,
            }

    async def get_series_i_summary(self, holdings_form_data):
        """
        # Get Series I Savings Bond Summary
        Submits the form from the Current Holdings page to get the bond summary.
        """
        url = f"{self.base_url}/RS/RSGatewayRW"
        headers = self.headers.copy()
        headers.update(
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"{self.base_url}/RS/RSGatewayRW?UIHandler=ch.DisplayCurrentHoldings&primary=true&processID={holdings_form_data['processID']}&fromTabLink=true&uiFrom=misc.DisplayWelcome",
            }
        )

        payload = {
            "seriesCode": holdings_form_data["seriesCode"],
            holdings_form_data["submit_name"]: "Submit",
            "processID": holdings_form_data["processID"],
            "primary": holdings_form_data["primary"],
        }

        async with self.session.post(url, headers=headers, data=payload) as response:
            response.raise_for_status()
            html = await response.text()
            soup = self._parse_html(html)

            summary_table = soup.find("table", class_="border")
            if not summary_table:
                return []

            bonds = []
            rows = summary_table.find_all("tr")
            for row in rows[1:]:  # Skip header row
                cols = row.find_all("td")
                if len(cols) == 7:
                    bond_data = {
                        "confirm_num": cols[1].text.strip(),
                        "issue_date": cols[2].text.strip(),
                        "interest_rate": cols[3].text.strip(),
                        "status": cols[4].text.strip() or "N/A",
                        "amount": cols[5].text.strip(),
                        "current_value": cols[6].text.strip(),
                    }
                    bonds.append(bond_data)
            return bonds

    async def login_and_get_bonds(self, username, password, otp):
        """High-level function to perform the full login and data retrieval."""
        print("Step 1: Getting initial login page...")
        csrf1 = await self.get_initial_login_page()
        print("Step 2: Submitting username...")
        csrf2 = await self.submit_username(username, csrf1)
        print("Step 3: Submitting One-Time Passcode (OTP)...")
        await self.submit_otp(otp, csrf2)
        print("Step 4: Getting password page...")
        csrf3 = await self.get_password_page()
        print("Step 5: Submitting password...")
        welcome_html = await self.submit_password(password, csrf3)
        print("Login successful! Welcome page received.")
        print("Step 6: Getting current holdings information...")
        holdings_data = await self.get_current_holdings(welcome_html)
        print("Step 7: Retrieving Series I bond summary...")
        bonds = await self.get_series_i_summary(holdings_data)
        return bonds

    async def calculate_bond_value(
        self, series, denomination, issue_date, redemption_date
    ):
        """
        # Calculate Savings Bond Value
        Calculates the value of a paper savings bond.
        """
        url = f"{self.base_url}/BC/SBCPrice"
        headers = self.headers.copy()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        payload = {
            "RedemptionDate": redemption_date,
            "Series": series,
            "Denomination": denomination,
            "IssueDate": issue_date,
            "btnAdd.x": "CALCULATE",
            "SerialNumber": "",
            "SerialNumList": "",
            "IssueDateList": "",
            "SeriesList": "",
            "DenominationList": "",
            "IssuePriceList": "",
            "InterestList": "",
            "YTDInterestList": "",
            "ValueList": "",
            "InterestRateList": "",
            "NextAccrualDateList": "",
            "MaturityDateList": "",
            "NoteList": "",
            "OldRedemptionDate": "",
            "ViewPos": "0",
            "ViewType": "Partial",
            "Version": "6",
        }

        async with self.session.post(url, headers=headers, data=payload) as response:
            response.raise_for_status()
            html = await response.text()
            soup = self._parse_html(html)

            # Check for errors
            error_div = soup.find("div", class_="error")
            if error_div:
                errors = [li.text.strip() for li in error_div.find_all("li")]
                raise ValueError(f"Error calculating bond value: {'; '.join(errors)}")

            # Extract data from the main summary table
            summary_table = soup.find("table", id="ta1")
            if summary_table:
                header_row = summary_table.find("tr")
                data_row = header_row.find_next_sibling("tr")
                headers = [th.text.strip() for th in header_row.find_all("th")]
                values = [td.text.strip() for td in data_row.find_all("td")]
                return dict(zip(headers, values))

            raise ValueError(
                "Could not find the bond value summary table in the response."
            )


async def main():
    """Main function to run the API via command-line inputs."""
    api = TreasuryDirectAPI()
    try:
        print("TreasuryDirect API Client")
        print("-------------------------")
        print("1. Calculate Paper Savings Bond Value (No Login Required)")
        print("2. Log In and Get My Series I Bond Holdings")

        choice = input("Enter your choice (1 or 2): ")

        if choice == "1":
            print("\n--- Calculate Paper Bond Value ---")
            series = input("Enter Bond Series (e.g., I, EE, E): ").upper()
            denomination = input("Enter Bond Denomination (e.g., 50, 100, 500): ")
            issue_date = input("Enter Issue Date (MM/YYYY): ")
            today = datetime.now()
            redemption_date = input(
                f"Enter Redemption Date (MM/YYYY) [Default: {today.strftime('%m/%Y')}]: "
            ) or today.strftime("%m/%Y")

            try:
                result = await api.calculate_bond_value(
                    series, denomination, issue_date, redemption_date
                )
                print("\n--- Bond Value Result ---")
                for key, value in result.items():
                    print(f"{key}: {value}")
                print("-------------------------")
            except ValueError as e:
                print(f"\nError: {e}", file=sys.stderr)

        elif choice == "2":
            print("\n--- Log In to TreasuryDirect ---")
            username = input("Enter your Account Number: ")
            password = input("Enter your Password: ")
            print("\nA One-Time Passcode (OTP) will be sent to your registered email.")
            otp = input("Enter the OTP from your email: ")

            try:
                bonds = await api.login_and_get_bonds(username, password, otp)
                if bonds:
                    print("\n--- Your Series I Savings Bonds ---")
                    for bond in bonds:
                        print(
                            f"  Confirm #: {bond['confirm_num']}, "
                            f"Issue Date: {bond['issue_date']}, "
                            f"Rate: {bond['interest_rate']}, "
                            f"Amount: {bond['amount']}, "
                            f"Current Value: {bond['current_value']}"
                        )
                    print("-----------------------------------")
                else:
                    print("\nNo Series I Savings Bonds found in your account.")
            except ValueError as e:
                print(f"\nLogin or Data Retrieval Failed: {e}", file=sys.stderr)
            except aiohttp.ClientResponseError as e:
                print(f"\nHTTP Error: {e.status} - {e.message}", file=sys.stderr)

        else:
            print("Invalid choice. Please run again and enter 1 or 2.")

    finally:
        await api.close()


if __name__ == "__main__":
    # Helper to find sibling by text for bs4, which lacks a direct method
    def find_next_sibling_text(tag, text):
        parent = tag.find_parent()
        for sibling in parent.find_all(recursive=False):
            if sibling.text.strip() == text:
                return True
        return False

    BeautifulSoup.find.__globals__["find_next_sibling_text"] = find_next_sibling_text

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
