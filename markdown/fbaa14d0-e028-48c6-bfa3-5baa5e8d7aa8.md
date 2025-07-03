# Submit One-Time Passcode (OTP)

This API call submits the One-Time Passcode (OTP) received by the user.

## Request

### Method and URL

POST `https://treasurydirect.gov/RS/OTP-Submit.do`

### Headers

| Header           | Description                                                                | Required |
|------------------|----------------------------------------------------------------------------|----------|
| `Host`           | The server address.                                                        | Yes      |
| `Accept`         | Specifies the acceptable content types for the response.                   | Yes      |
| `Accept-Language`| Specifies the preferred language for the response.                         | Yes      |
| `Accept-Encoding`| Specifies the acceptable encoding types for the response.                  | Yes      |
| `Content-Type`   | Indicates the format of the request body.                                  | Yes      |
| `Origin`         | The origin of the request.                                                 | Yes      |
| `User-Agent`     | Identifies the client making the request.                                  | Yes      |
| `Referer`        | The URL of the previous page from which the request was made.              | Yes      |
| `Content-Length` | The length of the request body.                                            | Yes      |
| `Connection`     | Controls whether the network connection stays open after the transaction completes. | Yes      |
| `Cookie`         | Contains session and tracking information.                                 | Yes      |

### Body

The request body is sent in `application/x-www-form-urlencoded` format.

| Parameter   | Type   | Description                                                                                        | Example Value                                          |
|-------------|--------|----------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| `otp`       | string | The One-Time Passcode received by the user.                                                        | `xxxxxx`                                               |
| `_csrf`     | string | A Cross-Site Request Forgery token, typically extracted from the previous HTML response.           | `a1b2c3d4-e5f6-7890-1234-567890abcdef`                   |
| `enter.x`   | string | A parameter indicating the submission action, often set to 'Submit'.                               | `Submit`                                               |

**Example Request Body:**

```
otp=123456&enter.x=Submit&_csrf=a1b2c3d4-e5f6-7890-1234-567890abcdef
```

## Response

### Status Code and Headers

A successful response will result in a `302 Found` status code, indicating a redirect.

| Header     | Description                                                                                                                               | Example Value                                                                                                                                                                                                                                                                                                                                                                                                     |
|------------|-------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Location` | The URL to which the client should be redirected upon a successful OTP submission. This typically points to the password entry page.      | `https://treasurydirect.gov/RS/PW-Display.do`                                                                                                                                                                                                                                                                                                                                                                    |
| `Cache-Control`| Directs the client not to cache the response.                                                                                             | `no-store`                                                                                                                                                                                                                                                                                                                                                                                                    |
| `Content-Type`| Indicates the type of content in the response body. For a 302 redirect, this is often `text/plain` or similar as the body is empty. | `text/plain`                                                                                                                                                                                                                                                                                                                                                                                                    |

### Body

The response body for a successful redirect is typically empty.

**Example Response Body:**

(Empty)