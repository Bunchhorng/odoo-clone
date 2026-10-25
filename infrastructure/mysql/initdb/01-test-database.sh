#!/bin/bash
set -eu

# The official entrypoint sources this script during first initialization.
# Restrict interpolated identifiers and escape SQL LIKE wildcards in GRANT.
case "$MYSQL_DATABASE" in
  ''|*[!a-zA-Z0-9_]*) echo "MYSQL_DATABASE must contain only letters, digits, and underscores" >&2; exit 1 ;;
esac
case "$MYSQL_USER" in
  ''|*[!a-zA-Z0-9_]*) echo "MYSQL_USER must contain only letters, digits, and underscores" >&2; exit 1 ;;
esac

test_database="test_${MYSQL_DATABASE}"
grant_database="${test_database//_/\\_}"
MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=socket --user=root <<SQL
GRANT ALL PRIVILEGES ON \`${grant_database}\`.* TO '${MYSQL_USER}'@'%';
SQL
