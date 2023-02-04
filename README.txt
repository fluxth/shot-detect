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
    4. Export CSV
        - To be implemented.
    5. Change/Delete GOOGLE_APPLICATION_CREDENTIALS
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

Correction function guide:
- The correction function allows the user to edit the shot detection results
  from Google API. You will need to run the detection function on the video
  first.
- You should run the video through the `Generate Preview Subtitle` first (guide
  below), and check in your video player (VLC or mpv is recommended) which
  automatically detected shots are problematic. If you use mpv, you can click
  the time indicator to the left of the seek bar to display a full timecode.
- To correct the shot detection result for a video,
    - First, enter the same URI you did for the detection function.
    - It will automatically detect the models you use and generate the OVERLAY
      file for you to edit. These files should be named
      `OVERLAY_builtin-stable.txt` or `OVERLAY_builtin-latest.txt` depending on
      the models you used.
    - If you previously used the correction function before, and the program
      detected an existing OVERLAY file, it will ask if you want to regenerate
      a new overlay file and overwrite (in case the old one was damaged).
      Answer with `y` or `n` key for yes or no.
    - After the files are generated. The program will wait for you to edit the
      files.
    - If you leave an OVERLAY file unedited, the program will not edit anything,
      essentially bypassing this function. This is useful when you use multiple
      models, stable and latest, and want to only edit only one model.
    - If you want to clear all manual edits, overwrite all the OVERLAY files
      and don't edit anything, this will return your state to the original AI
      shot change detection.
    - To edit an OVERLAY file, open that file (eg. `OVERLAY_builtin-stable.txt`)
      with your favorite text editor, TextEdit on macOS works fine, but be sure
      to turn off the auto-correct function.
    - Make edits in that file,
        - You will see some instructions at the top of the file, these lines
          start with a `#` character and are ignored in processing.
        - You will see lines that look like:
          `keep 10 0:00:00.26 -> 0:00:00.76`
          These are your detected shot entries. They are space-separated
          words that tell the program what to do when making manual edits.
        - The most important words are the first and second.
            1. The first is the "action" word, this tells the program how to
               edit this shot.
            2. The second word is the "Shot ID" word, when used with a manually
               added shot (eg. with `split` or `add`) this word is just a label
               for you to keep track of what shot this is when playing it back
               in the player. It doesn't need to be ordered in anyway, in fact,
               it doesn't even need to be a number, it can be any text without
               space. The shot IDs generated by default are in a multiple of 10
               because it is easier to add shots between automatically detected
               shots, For example: between shot 10 and 20 is 15. When a shot is
               deleted or merged, shot IDs can skip from 30 to 60, this is
               totally fine and won't affect the final computation for the CSV.
               If used with an
        - There are 3 main ways that you will most likely use while editing,
            1. Not editing a line, if the first word is `keep`, the program
               will ignore any edits to this shot. (Even if you edit the
               timecode behind it, the program won't do anything)
            2. If you change the first word to `mergeup` or `mergedown`,
               the program will merge the shot of that line up to the previous
               shot, or down to the next shot. The is useful when the AI
               detected an extra cut that isn't supposed to be there.
               The mergeup and mergedown word will ignore everything behind it.
               In fact, you can delete everything behind the first word and it
               will work just fine.
            3. If you add a new line with the first word of "split", it will
               automatically make a cut in-between the previous shot. You will
               need to specify a new shot ID and a timecode to cut following
               the "split" word, separated by spaces. It should be like the
               following example:

                    keep 70 0:00:05.77 -> 0:00:07.64
                    split 75 0:00:06.00
                    keep 80 0:00:07.67 -> 0:00:17.91

               This will cut shot 70 end at 00:06.00, and create a shot 75 at
               00:06.00 to 00:07.64.
               You can even do multiple splits:

                    keep 70 0:00:05.77 -> 0:00:07.64
                    split 72 0:00:06.00
                    split 77 0:00:07.00
                    keep 80 0:00:07.67 -> 0:00:17.91

               This will cut shot 70 end at 00:06.00, create a shot 72 at
               00:06.00 to 00:07.00, and create a shot 77 at
               00:07.00 to 00:07.64.

        - The remaining actions (first words) are for advanced editing, they
          can be referenced to in the help text at the top of every OVERLAY
          file.
        - Do NOT just delete any "keep" lines, it will throw the program out of
          sync, use the "delete" action for deleting shots without merging.
    - Remember to save the file after you're done.
    - Go back to the program, and press enter.
    - If a success message is shown, your edits are saved and you can proceed
      to either generating a preview subtitle, or exporting a CSV.

Generate Preview Subtitle function guide:
- This function will generate a preview subtitle from whichever the newest data
  it has. If it has only the automatically generated shot-detection, it will
  generated from that. In contrary, if it detects a manually corrected shots
  from the correction function, it will use that instead.
- When successful, this function will generate '.ass' subtitle with the names of
  `preview_builtin-stable.ass` or `preview_builtin-latest.ass` depending on what
  model you used. Import this subtitle file to your video player to check shot
  alignment.
