CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    mobile_number VARCHAR(20),
    password VARCHAR(255) NOT NULL,
    followers_count INT DEFAULT 0,
    following_count INT DEFAULT 0,
    uploads_count INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS content (
    content_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(255) NOT NULL,
    media_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    language VARCHAR(50),
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS follow (
    follow_id INT AUTO_INCREMENT PRIMARY KEY,
    follower_user_id INT,
    following_user_id INT,
    FOREIGN KEY(follower_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(following_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(follower_user_id, following_user_id)
);
