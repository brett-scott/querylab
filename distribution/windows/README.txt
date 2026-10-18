QueryLab Helper for Windows - developer preview 0.4.1

1. Install Docker Desktop for Windows from the official website:
   https://docs.docker.com/desktop/setup/install/windows-install/
   Complete its setup, select Linux containers and wait for Engine running.
   Docker Desktop has its own system requirements and licence terms.

2. Right-click the downloaded ZIP and choose Extract All. Extract to a folder
   you can write to, such as Documents\QueryLab-Helper. Do not run inside the ZIP.

3. Open Start-QueryLab-Helper.cmd in the extracted folder. No Git, Node or Python
   installation is needed. Windows may show a security prompt because this
   developer preview is unsigned. Only run files from a source you trust.

4. On the QueryLab website choose Copy website address. Paste that address into
   the launcher. Only trust a website you recognise: it will be allowed to send
   practice queries to this local helper after you pair.

5. Choose Start helper. The first launch downloads Docker images and builds the
   helper; it may take several minutes and needs internet access and disk space.
   Later launches reuse the installed images and your saved local configuration.

6. When the launcher says Ready, choose Copy pairing code. Return to QueryLab.
   Keep the prefilled Helper URL unless the launcher shows a different port,
   paste into Pairing code and choose Pair helper.

The helper binds to 127.0.0.1 only. MySQL is private to the local Docker network.
Closing the launcher window DOES NOT stop the helper or MySQL. To stop them,
open Docker Desktop and stop the querylab-installed-... project for this folder.
To reconnect, reopen Start-QueryLab-Helper.cmd and choose Start helper again.

Keep the folder, pairing code and .env.helper private. Never upload .env.helper
or share a configured installation. It contains local database credentials.
Keep .env.helper with its Docker volume: changing credentials or the namespace
can disconnect your installation from its saved database.

If startup fails, the launcher keeps your settings and displays recovery steps.
Check Docker Desktop is running Linux containers, has internet access and free
disk space. Retry Start helper after correcting the problem. Do not delete your
configuration or volumes to retry. Port conflicts are reported before startup.

Advanced: Existing MySQL is optional. Configure MYSQL_HOST, MYSQL_PORT,
MYSQL_ROOT_USER and MYSQL_ROOT_PASSWORD in .env.helper before starting. A host
server is normally host.docker.internal from Docker Desktop. Use a dedicated
practice instance meeting QueryLab's MySQL 8.4 requirements. The launcher keeps
existing credentials and does not start bundled MySQL when MYSQL_HOST differs
from mysql. An incompatible server is reported without changing global settings.

This preview has not yet been certified on a clean Windows computer. Public
HTTPS-to-localhost browser permissions still require end-to-end verification.
