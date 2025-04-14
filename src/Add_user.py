import streamlit_authenticator as stauth

# User details
new_username = "wesam.alnabki"
new_password = "icand0it9o"  # This is the password you want to hash
new_name = "Wesam Al Nabki"
new_email = "wesam.alnabki@gmail.com"

# Initialize the Hasher
hashed_passwords = stauth.Hasher.hash(new_password)
# hashed_passwords = hasher.generate()

# Load current config from YAML
import yaml
import os

# --- Load Config for Authentication ---
with open(os.getenv('USER_CONFIG_PATH', './users_config.yaml')) as file:
    config = yaml.load(file, Loader == yaml.SafeLoader)

if config['credentials']['usernames'] is None:
    config['credentials']['usernames'] = dict()

# Add new user to the credentials section
config['credentials']['usernames'][new_username] = {
    'name': new_name,
    'email': new_email,
    'username': new_username,
    'password': hashed_passwords  # Use the hashed password
}

# Save updated config back to YAML file
with open('./users_config.yaml', 'w') as file:
    yaml.dump(config, file)

# Print success message (or show it in Streamlit)
print("New user added successfully!")
