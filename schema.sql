create database if not exists glassboard_db;
use glassboard_db;

create table if not exists modules (
    id int auto_increment primary key,
    name varchar(50) not null unique,
    description varchar(200)
) ENGINE=InnoDB;

create table if not exists tasks (
    id bigint auto_increment primary key,
    title varchar(100) not null,
    is_complete boolean default false,
    module_id int not null,
    foreign key (module_id) refernces moudules(id) on delete cascade
) ENGINE=InnoDB;