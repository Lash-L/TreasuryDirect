# Retrieve Login Page CSRF Token

This API call retrieves the initial login page for the TreasuryDirect application. The response contains a hidden input field named `_csrf` which is crucial for subsequent authenticated requests.

## Request

### Method and URL

```http
GET https://treasurydirect.gov/RS/UN-Display.do
```

### Headers

| Header          | Value                                                                                                                                                                                                                                                                                                   | Description                                                                               |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `Host`          | `treasurydirect.gov`                                                                                                                                                                                                                                                                                      | The domain name of the server.                                                            |
| `Cookie`        | `_4c_=%7B%22_4c_s_%22%3A%22...%22%7D; BIGipServer7O23MOP7RgI1gYLFruriRw=!...; TS0101dd88=REDACTED` | Contains session and tracking cookies. This should be obtained from previous requests. |
| `User-Agent`    | `Mozilla/5.0 (iPhone; CPU iPhone OS 19_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Brave/1 Mobile/15E148 Safari/604.1`                                                                                                                                                                         | The user agent string of the client.                                                      |
| `Accept`        | `text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8`                                                                                                                                                                                                                                       | The accepted content types for the response.                                              |
| `Accept-Language` | `en-US,en;q=0.9`                                                                                                                                                                                                                                                                                          | The preferred language for the response.                                                  |
| `Connection`    | `keep-alive`                                                                                                                                                                                                                                                                                              | Keep the connection open for subsequent requests.                                         |
| `Sec-Fetch-Site`| `none`                                                                                                                                                                                                                                                                                                    | Indicates the relationship between the request initiator and the origin server.         |
| `Sec-Fetch-Mode`| `navigate`                                                                                                                                                                                                                                                                                                | The mode of the request.                                                                  |
| `Sec-Fetch-Dest`| `document`                                                                                                                                                                                                                                                                                                | The type of resource requested.                                                           |

### Request Body

This request does not have a request body.

## Response

### Status Code and Headers

*   **Status Code**: `200 OK`
*   **Content-Type**: `text/html; charset=ISO-8859-1`
*   **Set-Cookie**: Multiple `Set-Cookie` headers are present for session management.

### Response Body

The response body is an HTML document containing the login form. The critical element to extract is the `value` attribute of the hidden input field named `_csrf`.

```html
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
	<title>Access Your TreasuryDirect Account</title>
    <!-- ... other head elements ... -->
</head>
<body>
    <!-- ... other body content ... -->
    <form action="/RS/UN-Submit.do" method="post" id="Login" name="Login">
        <!-- ... form elements ... -->
        <input type="hidden" name="_csrf" value="c5ff86ca-511c-48cf-54c5-21f261df4cz9" />
        <!-- ... other form elements ... -->
    </form>
    <!-- ... other body content ... -->
</body>
</html>
```

### Extraction

To proceed with subsequent login requests, you need to extract the `value` from the `_csrf` hidden input field. In the example above, this value is `c5ff86ca-511c-48cf-54c5-21f261df4cz9`.