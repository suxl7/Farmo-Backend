# Frontend Integration Guide for Farmo Backend

This guide provides instructions for frontend developers (React and Android) on how to connect to the Farmo backend server.

## Running the Development Server

To start the backend server, run the following command in the project's root directory:

```bash
python manage.py runserver
```

By default, the server will be accessible at `http://127.0.0.1:8000`.

## Connecting from Different Devices on the Same Network

To connect to the development server from a different device (e.g., a mobile phone for Android development) on the same network, you need to:

1.  **Find your computer's local IP address.**
    *   **Windows:** Open Command Prompt and type `ipconfig`. Look for the "IPv4 Address" under your active network adapter.
    *   **macOS/Linux:** Open a terminal and type `ifconfig` or `ip a`. Look for the `inet` address.

2.  **Add the IP address to `ALLOWED_HOSTS` in `Farmo/settings.py`.**

    Open the `Farmo/settings.py` file and add your local IP address to the `ALLOWED_HOSTS` list. For example, if your IP is `192.168.1.10`, the file should look like this:

    ```python
    # Farmo/settings.py

    ALLOWED_HOSTS = [*, '127.0.0.1', 'localhost']
    ```

3.  **Use the IP address in your frontend application's API calls.**

    Replace `127.0.0.1:8000` or `localhost:8000` with `<your-local-ip>:8000`. For example: `http://192.168.1.10:8000/api/auth/login/`.

## API Endpoints

Here are the key endpoints for authentication and core features:

### Base URL

*   **Same Device:** `http://127.0.0.1:8000`
*   **Different Device:** `http://<your-local-ip>:8000` (replace `<your-local-ip>` with your actual IP)

---

### 1. User Signup

*   **Endpoint:** `/api/auth/register/`
*   **Method:** `POST`
*   **Description:** Registers a new user.
*   **Body (raw JSON):**
    ```json
    {
        "user_id": "newuser",
        "email": "user@example.com",
        "password": "yourpassword",
        "user_type": "farmer"
    }
    ```
*   **React Example:**
    ```javascript
    fetch('http://127.0.0.1:8000/api/auth/register/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_id: 'newuser',
            email: 'user@example.com',
            password: 'yourpassword',
            user_type: 'farmer', // or 'consumer'
        }),
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error('Error:', error));
    ```

### 2. User Login

*   **Endpoint:** `/api/auth/login/`
*   **Method:** `POST`
*   **Description:** Logs in a user and returns a token.
*   **Body (raw JSON):**
    ```json
    {
        "user_id": "testuser",
        "password": "yourpassword"
    }
    ```
*   **React Example:**
    ```javascript
    fetch('http://127.0.0.1:8000/api/auth/login/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_id: 'testuser',
            password: 'yourpassword',
        }),
    })
    .then(response => response.json())
    .then(data => {
        console.log(data);
        // Save the token for future requests
        localStorage.setItem('authToken', data.token);
    })
    .catch(error => console.error('Error:', error));
    ```

### 3. Verification Request

*   **Endpoint:** `/api/user/verification-request/`
*   **Method:** `POST`
*   **Description:** Submits a verification request for a user. This requires a token from login.
*   **Headers:**
    ```
    Authorization: Token <your_auth_token>
    ```
*   **Body (form-data):** This endpoint likely expects `multipart/form-data` for file uploads.
*   **React Example:**
    ```javascript
    const formData = new FormData();
    formData.append('document_type', 'citizenship'); // or 'passport', etc.
    formData.append('document_front', fileInput.files[0]); // from an <input type="file">
    formData.append('document_back', fileInput2.files[0]);
    formData.append('selfie', fileInput3.files[0]);

    fetch('http://127.0.0.1:8000/api/user/verification-request/', {
        method: 'POST',
        headers: {
            'Authorization': `Token ${localStorage.getItem('authToken')}`,
        },
        body: formData,
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error('Error:', error));
    ```

### 4. Add Product

There isn't a specific endpoint for adding products in the provided `urls.py`. You may need to consult `backend/service_frontend/product.py` or other view files to find the correct endpoint and its required parameters. Once found, the request structure would be similar to the "Verification Request" example if it involves image uploads.

## Notes for Android Developers

For Android development, you can use libraries like **Retrofit** or **OkHttp** to make network requests. The concepts are the same as the `fetch` examples above.

*   **Base URL:** Set the base URL in your Retrofit instance (`http://<your-local-ip>:8000/`).
*   **Endpoints:** Define the API endpoints as interfaces in Retrofit.
*   **Data Models:** Create Kotlin/Java classes that match the JSON structures for request and response bodies.
*   **Authorization:** Use an OkHttp Interceptor to add the `Authorization` header to requests that require authentication.
*   **File Uploads:** Use `@Multipart` annotations in Retrofit to handle `multipart/form-data` requests for endpoints like `verification-request`.

Remember to request the `android.permission.INTERNET` permission in your `AndroidManifest.xml`.
```xml
<uses-permission android:name="android.permission.INTERNET" />
```