# Frontend Deployment on Firebase

This guide provides step-by-step instructions to deploy and host the frontend of the Buffs E-Commerce platform using Firebase Hosting.

## Prerequisites

1. [Node.js](https://nodejs.org/) installed on your system (preferably the latest LTS version).
2. A [Firebase account](https://firebase.google.com/) with a Firebase project created.
3. Firebase CLI installed on your machine. If not installed, run the following command:
   ```bash
    npm install -g firebase-tools
   ```

## Deployment Steps

1. **Navigate to the Frontend Code Directory**:
   - Open a terminal and ensure you are in the directory containing the frontend code.

    ```bash
     cd <path of the frontend files>
    ```
2. **Install the necessary dependencies and build the Frontend**:

    ```bash
    npm install
    npm run build
    ``` 
3. **Host the Frontend on Firebase**:

    ```bash
    firebase login
    firebase init hosting
    ```
    - Select Firebase project: Choose the Firebase project created for Buffs E-Commerce.
    - Specify public directory: Enter the directory containing your built files (e.g., build or dist).
    - Single-page application: Respond with Yes to configure as a single-page app (rewrites all URLs to index.html).
    - Overwrite existing files: Select No unless you’re sure.

    **Deploy the frontend**

    ```
    firebase deploy
    ```

    After deployment, Firebase will provide a hosting URL. Visit the provided URL to see your deployed frontend.
