import streamlit_authenticator as stauth

# User details
new_username = "admin"
new_password = "admin"  # This is the password you want to hash
new_name = "admin"
new_email = "admin@gmail.com"

# Initialize the Hasher
hashed_passwords = stauth.Hasher.hash(new_password)
# hashed_passwords = hasher.generate()

# Load current config from YAML
import yaml
import os

# --- Load Config for Authentication ---
config_path = os.getenv("USER_CONFIG_PATH", "../DATA/users_config.yaml")
with open(config_path) as file:
    config = yaml.load(file, Loader=yaml.SafeLoader)

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
with open(config_path, 'w') as file:
    yaml.dump(config, file)

# Print success message (or show it in Streamlit)
print("New user added successfully!")
