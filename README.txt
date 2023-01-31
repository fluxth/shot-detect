Shot change detection program

Installation:
- Before first run, double click on `install.command`

API Key Setup:
- To start the program, double click on `start.command`
- You will be asked for GOOGLE_APPLICATION_CREDENTIALS
    - Get this from the Google Cloud console, on the `Credentials` page
    - Click `Create Credentials` -> `Service Account`
    - Give it some name, and grant it the `Owner` permission
    - Create the account
    - Once you're back to the list page, click the pencil icon on your new
      service account
    - Go to the `Keys` tab
    - Click `Add Key` -> `Create New Key`
    - Select JSON and click create
    - Download the key, please make note of where you save it.
- Activate the Video Intelligence API in the Google Cloud web console
    - Go to `API & Services`
    - Search for 'Cloud Video Intelligence API'
    - Enable the API
- When the program asks you for the JSON file, drag the key file that you just
  downloaded into the terminal and press enter
- This should bring you to the main menu screen of the program

Usage:
- To start the program, double click on `start.command`
- Select the function on the main menu, the main functions are:
    1. Detection 
        - Use Google Cloud Video Intelligence API to detect shots changes in
          your video, this will save the detection result for other functions,
          so you only need to run this once per video.
    2. Correction
        - Manually correct the shot change detection of a video, note that the
          video needs to be ran through the detection function first.
    3. Generate Preview Subtitle
        - Uses the data from the detection stage (and if available, correction
          stage to generate preview subtitle file (.ass) that can be loaded into
          a video player to check the detected shot changes.
    4. Change/Delete GOOGLE_APPLICATION_CREDENTIALS
        - If you happen to change the credentials JSON file, use these functions
          to update your credentials.
- In order to start detection on a video, the video itself needs to be uploaded
  to Google Cloud Storage.
    - Create a Google Cloud Storage bucket if you haven't done it already.
        - Go to 'https://console.cloud.google.com/storage/'
        - Click `Create`
        - Give it a name
        - Select `Region`, then `asia-southeast1 (Singapore)` 
        - Use `Set a default class` and `Standard` storage class
        - Click `Create`
    - Upload your video files to the created bucket, there should be a web
      interface, similar to Google Drive to do this.
    - Get the URI to paste into this program by clicking the file in the
      Google Cloud Storage file list and click `Copy gsutil URI`.

Important Note:
- Remember to delete all buckets and their contents after use. You'll be
  charged for storage after the free trial expires.
