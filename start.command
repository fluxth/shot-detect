#!/bin/bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

print_uri_prompt(){
    echo "Please enter a Google Cloud Storage URI for your desired video"
    echo "The URI should be in this format: 'gs://bucket/folder/video.mp4'"

    echo -en "\033[33m\033[1m"
    echo -n "URI > "
    echo -en "\033[0m"
}

menu(){
    echo
    echo -en "\033[36m\033[1m"
    echo "MAIN MENU: Please select your desired function"
    echo -en "\033[0m"
    echo -en "\033[1m"
    echo "[1] Detection"
    echo "[2] Correction"
    echo "[3] Generate Preview Subtitle"
    echo "[4] Export CSV"
    echo -en "\033[0m"
    echo "[5] Change GOOGLE_APPLICATION_CREDENTIALS"
    echo "[6] Delete saved GOOGLE_APPLICATION_CREDENTIALS"
    echo "[q] Quit Program"

    echo -en "\033[33m\033[1m"
    echo -n "Your selection > "
    echo -en "\033[0m"
    read -n1 selection
    echo
    echo

    case "$selection" in
        "1")
            echo -en "\033[36m\033[1m"
            echo "SHOT DETECTION"
            echo -en "\033[0m"
            echo "Starting shot detection for a new video"
            print_uri_prompt
            read uri
            echo
            echo -en "\033[36m\033[1m"
            echo "SHOT DETECTION: MODEL"
            echo -en "\033[0m"
            echo "Please select a model to use for shot change detection"
            echo "[1] builtin/stable"
            echo "[2] builtin/latest"
            echo -en "\033[33m\033[1m"
            echo -n "Your selection > "
            echo -en "\033[0m"
            read -n1 model_selection
            echo
            echo

            case "$model_selection" in
                "1")
                    run_python detect --uri "$uri" --model builtin/stable
                    ;;
                "2")
                    run_python detect --uri "$uri" --model builtin/latest
                    ;;
                *)
                    echo -en "\033[31m"
                    echo "Unknown selection!"
                    echo "Make sure to enter the character in [square brackets]"
                    echo -en "\033[0m"
                    echo
                    ;;
            esac
            ;;
        "2")
            echo -en "\033[36m\033[1m"
            echo "SHOT CORRECTION"
            echo -en "\033[0m"
            echo "Correcting shot detect data for a video"
            print_uri_prompt
            read uri
            echo
            run_python correct --uri "$uri"
            ;;
        "3")
            echo -en "\033[36m\033[1m"
            echo "GENERATE PREVIEW SUBTITLE"
            echo -en "\033[0m"
            print_uri_prompt
            read uri
            echo
            run_python preview --uri "$uri"
            ;;
        "4")
            run_python export
            ;;
        "5")
            echo -en "\033[36m\033[1m"
            echo "CHANGE API KEY"
            echo -en "\033[0m"
            change_api_key
            ;;
        "6")
            rm -f "$SCRIPT_DIR/.env"
            export GOOGLE_APPLICATION_CREDENTIALS=
            echo -en "\033[32m"
            echo "Previously saved GOOGLE_APPLICATION_CREDENTIALS deleted!"
            echo -en "\033[0m"
            return 0
            ;;
        "q")
            echo -en "\033[32m"
            echo "Program exited!"
            echo "You can now close this terminal window"
            echo -en "\033[0m"
            return 1
            ;;
        *)
            echo -en "\033[31m"
            echo "Unknown selection!"
            echo "Make sure to enter the character in [square brackets]"
            echo -en "\033[0m"
            return 0
            ;;
    esac
}

load_env(){
    if [[ -f "$SCRIPT_DIR/.env" ]]; then
      export $(cat "$SCRIPT_DIR/.env" | xargs)
    fi
}

source_venv(){
    if [[ -f "$SCRIPT_DIR/venv/bin/activate" ]]; then
        source "$SCRIPT_DIR/venv/bin/activate"
    fi
}

check_api_key(){
    while [[ "$GOOGLE_APPLICATION_CREDENTIALS" == "" ]]; do
        echo
        echo -en "\033[31m\033[1m"
        echo "Warning: GOOGLE_APPLICATION_CREDENTIALS is not set"
        echo "Please follow the instructions to set your API credentials"
        echo -en "\033[0m"
        echo
        echo -en "\033[36m\033[1m"
        echo "API KEY SETUP"
        echo -en "\033[0m"
        change_api_key
        load_env
    done

    set +e
    local verified="$(run_python_impl verify)"
    set -e
    if [[ "$verified" != "OK" ]]; then
        echo
        echo -en "\033[33m\033[1m"
        echo "Warning: Your GOOGLE_APPLICATION_CREDENTIALS may not be valid"
        echo "Please double check your credentials settings!"
        echo "The program will continue but please note that you will likely be encountering an error"
        echo -en "\033[0m"
    fi
}

change_api_key(){
    echo "Please obtain the credentials file from Google Cloud web console"
    echo "The resulting file should end with '.json' extension"
    echo "Drag and drop the '.json' file into this terminal window and press enter"
    echo "To cancel, just press enter without inputting anything"
    echo -en "\033[33m\033[1m"
    echo -n "Path to credentials JSON > "
    echo -en "\033[0m"
    read key_file
    local trimmed_key_file=$(echo "$key_file" | xargs)
    if [[ "$trimmed_key_file" == "" ]]; then
        echo -en "\033[31m"
        echo "Credentials setup cancelled"
        echo -en "\033[0m"
    elif [[ ! -f "$trimmed_key_file" ]]; then
        echo -en "\033[31m"
        echo "The file you inputted doesn't exist!"
        echo "Please recheck the path you inputted"
        echo -en "\033[0m"
        return 0
    else
        echo "GOOGLE_APPLICATION_CREDENTIALS=$trimmed_key_file" > "$SCRIPT_DIR/.env"
    fi
}

run_python_impl(){
    (cd "$SCRIPT_DIR" && python3 shot_detect.py $@)
}

run_python(){
    set +e
    run_python_impl $@
    local exit_code=$?
    set -e

    if [[ "$exit_code" == "0" ]]; then
        echo
        echo -en "\033[32m"
        echo "The operation completed successfully!"
        echo -en "\033[0m"
    else
        echo
        echo -en "\033[31m"
        echo "The operation failed with code: $exit_code"
        echo -en "\033[0m"
        #exit $exit_code
    fi
}

echo
echo -en "\033[36m\033[1m"
echo "Welcome to shot detect v0.1.0!"
echo -en "\033[0m"

while [[ "$?" == "0" ]]; do
    load_env
    source_venv
    check_api_key
    menu
done
