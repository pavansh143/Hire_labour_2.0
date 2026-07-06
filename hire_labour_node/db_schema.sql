CREATE DATABASE IF NOT EXISTS hire_labour_db;
USE hire_labour_db;

CREATE TABLE IF NOT EXISTS labourers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    location VARCHAR(255),
    skills TEXT,
    bio TEXT,
    aadhaar_number VARCHAR(20),
    id_card_image VARCHAR(255),
    selfie_image VARCHAR(255),
    profile_image VARCHAR(255),
    face_encoding TEXT,
    trust_score INT DEFAULT 0,
    status ENUM('Verified', 'Suspicious', 'Fake', 'Pending') DEFAULT 'Pending',
    otp_verified BOOLEAN DEFAULT FALSE,
    is_banned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS otp_verifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phone VARCHAR(20) NOT NULL,
    code VARCHAR(6) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    labourer_id INT NOT NULL,
    reviewer_name VARCHAR(255),
    rating INT CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    is_flagged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (labourer_id) REFERENCES labourers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Seed an admin (password: admin123)
INSERT IGNORE INTO admins (username, password) VALUES ('admin', '$2a$10$X7vH7Wv6eP3j0z2k.G6J2.M.1u7y9S4i.0S.1G.1G.1G.1G.1G.1G');
