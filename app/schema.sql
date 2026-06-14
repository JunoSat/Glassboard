create database if not exists glassboard_db;
use glassboard_db;

create table if not exists modules (
    id int auto_increment primary key,
    name varchar(50) not null unique,
    description text
) ENGINE=InnoDB;

create table if not exists users(
    id bigint auto_increment primary key,
    username varchar(50) not null unique,
    password_hashed varchar(255) not null,
    role enum ('admin', 'manager', 'member') not null default 'member',
    module_id int,
    foreign key (module_id) references modules(id) on delete set null
) ENGINE=InnoDB;

create table if not exists tasks (
    id bigint auto_increment primary key,
    title varchar(100) not null,
    description text,
    status varchar(20) default 'pending',
    module_id int not null,
    assigned_to bigint,
    foreign key (module_id) references modules(id) on delete cascade,
    foreign key (assigned_to) references users(id) on delete set null
) ENGINE=InnoDB;

create table if not exists audit_log(
    id bigint auto_increment primary key,
    target_table varchar(50) not null,
    row_id bigint not null,
    action_type enum('INSERT', 'DELETE', 'UPDATE') not null,
    old_value text,
    new_value text,
    changed_by_user_id bigint,
    timestamp datetime default CURRENT_TIMESTAMP,
    foreign key (changed_by_user_id) references users(id) on delete set null
) ENGINE=InnoDB;

create table if not exists handshakes(
    id bigint auto_increment primary key,
    task_id bigint not null,
    sender_module_id int not null,
    receiver_module_id int not null,
    status enum('PENDING', 'ACTIVE', 'REJECTED') not null default 'PENDING',
    requested_at datetime default CURRENT_TIMESTAMP,
    updated_at datetime default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
    foreign key (task_id) references tasks(id) on delete cascade,
    foreign key (sender_module_id) references modules(id) on delete cascade,
    foreign key (receiver_module_id) references modules(id) on delete cascade
) ENGINE=InnoDB;

DROP TRIGGER IF EXISTS after_task_insert;
CREATE TRIGGER after_task_insert
AFTER INSERT ON tasks
FOR EACH ROW
INSERT INTO audit_log (target_table, row_id, action_type, old_value, new_value)
VALUES ('tasks', NEW.id, 'INSERT', NULL, CONCAT('Title: ', NEW.title, ' | Status: ', NEW.status));


DROP TRIGGER IF EXISTS after_task_update;
CREATE TRIGGER after_task_update
AFTER UPDATE ON tasks
FOR EACH ROW
INSERT INTO audit_log (target_table, row_id, action_type, old_value, new_value)
VALUES ('tasks', NEW.id, 'UPDATE',
        CONCAT('Title: ', OLD.title, ' | Status: ', OLD.status),
        CONCAT('Title: ', NEW.title, ' | Status: ', NEW.status));


DROP TRIGGER IF EXISTS after_task_delete;
CREATE TRIGGER after_task_delete
AFTER DELETE ON tasks
FOR EACH ROW
INSERT INTO audit_log (target_table, row_id, action_type, old_value, new_value)
VALUES ('tasks', OLD.id, 'DELETE', CONCAT('Title: ', OLD.title, ' | Status: ', OLD.status), NULL);