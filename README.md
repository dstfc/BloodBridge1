## Blood-Bridge

DB Setup

CREATE DATABASE bloodbridge;

USE bloodbridge;

CREATE USER 'DBAdmin'@'localhost' IDENTIFIED BY 'bloodbridge';

GRANT SELECT, INSERT, UPDATE, DELETE ON bloodbridge.* TO 'DBAdmin'@'localhost';

FLUSH PRIVILEGES;

CREATE TABLE register ( id INT AUTO_INCREMENT PRIMARY KEY, fullname VARCHAR(255) NOT NULL, email VARCHAR(255) NOT NULL UNIQUE, password VARCHAR(255) NOT NULL, blood_type VARCHAR(10) );

CREATE TABLE request ( id INT AUTO_INCREMENT PRIMARY KEY, requester_id INT NOT NULL, location VARCHAR(255) NOT NULL, blood_type VARCHAR(10) NOT NULL, urgency VARCHAR(50), date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status VARCHAR(50) DEFAULT 'pending', FOREIGN KEY (requester_id) REFERENCES register(id) ON DELETE CASCADE );

EC2 Commands(use this commands only the first time when accessing the EC2)

sudo yum update -y

sudo yum install python3 -y

sudo yum install python3-pip -y

sudo pip3 install virtualenv

python3 -m venv venv

source venv/bin/activate

pip install flask

sudo yum install git -y

git clone

cd

pip install mysql-connector-python

python app.py
## AWS console screenshots# readme

![Instance creation](https://github.com/user-attachments/assets/779bc81f-dad2-4a58-a9e7-3f69c56558fc)

![Blood Bridge link](https://github.com/user-attachments/assets/f09e9bc5-016a-4b18-bffc-f7a70767c117)

![Application creation](https://github.com/user-attachments/assets/2baa8e98-288b-4f4a-8ace-1b40a59c907b)

## AWS console Demo video
https://drive.google.com/file/d/1c-Vy9E1K7yh6E_I1Lv3JRQMqWn6E-piE/view?usp=sharing



