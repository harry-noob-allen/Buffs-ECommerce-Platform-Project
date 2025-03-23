# Deploying the Cloud Function

This guide provides step-by-step instructions for deploying a Cloud Function using Google Cloud CLI. Follow the steps below to deploy the `<cloud_function>` backend service.

---

## Prerequisites

1. **Install Google Cloud CLI**: Ensure that you have the `gcloud` CLI installed on your system. [Download and install it here](https://cloud.google.com/sdk/docs/install) if you haven’t already.
2. **Google Cloud Project**: Confirm you have access to the Google Cloud project named `buffs-e-commerce-platform`.
3. **Authentication**: Log in to your Google Cloud account using the following command:

```
gcloud auth login
gcloud config set project <project_id>
```

---

## Deployment Steps

1. **Navigate to the Backend Code Directory**:
   - Open a terminal and ensure you are in the directory containing the backend code for `<cloud_function>`.

    ```
     cd <path of the cloud function backend>
    ```

2. **Run the Deployment Command**:

    - Use the following command to deploy the function.

    ```bash
        gcloud functions deploy <cloud_function_name>\
    --runtime python310 \
    --trigger-http \
    --allow-unauthenticated \
    --project buffs-e-commerce-platform
    ```