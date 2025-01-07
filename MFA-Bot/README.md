# MFA-Bot Installation Guide

The **MFA-Bot** is designed for use with **Botworks**. Follow the steps below to set up and run the MFA-Bot on your system.

---

## **Prerequisites**
Ensure the following packages are installed on your system:

```bash
sudo apt-get install git nano sudo curl
```

If any of these are not already installed, the command above will take care of it.

---

## **Installation Steps**

1. **Clone the Repository**
   Clone the MFA-Bot repository from GitHub:
   ```bash
   git clone https://github.com/Len-PGH/SignalWire_python_AI_examples.git
   ```

2. **Navigate to the MFA-Bot Folder**
   Change into the directory containing the MFA-Bot script:
   ```bash
   cd SignalWire_python_AI_examples/MFA-Bot
   ```

3. **Make the Install Script Executable**
   Update the script permissions to allow execution:
   ```bash
   chmod +x install-mfa-bot-v1.sh
   ```

4. **Run the Install Script**
   Execute the installation script to set up dependencies:
   ```bash
   ./install-mfa-bot-v1.sh
   ```

5. **Edit and Populate the `.env` Credentials**
   After the installation script completes, open the `.env` file to configure your credentials:
   ```bash
   cp changeme.env .env && nano .env
   ```
   Populate the required fields with your credentials (e.g., API keys, URLs, etc.) and save the file.

6. **Activate the Virtual Environment**
   Once the script completes, activate the Python virtual environment:
   ```bash
   source venv/bin/activate
   ```

7. **Run the Application**
   Start the MFA-Bot application:
   ```bash
   python3 app.py
   ```

8. **Set Your Ngrok URL in Botworks**
   Obtain your ngrok URL that was created during the installation process and set it up in the **Botworks** platform to enable external connectivity.

---



Now you're ready to use **MFA-Bot** with **Botworks**! 🚀

