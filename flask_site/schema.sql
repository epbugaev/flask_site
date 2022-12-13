drop table if exists users;

create table users (
    id INTEGER primary key autoincrement,
    login TEXT not null,
    password TEXT not null,
    first_name TEXT,
    last_name TEXT, 
    header TEXT,
    experience TEXT,
    achievments TEXT, 
    img BLOB
);
