#ifndef AUTHSESSION_H
#define AUTHSESSION_H

#include <QObject>
#include <QString>
#include <QSettings>

class ApiClient;

// Mirrors frontend/src/app/services/auth.service.ts: holds the current
// session and drives login / guest-login / token-restore / logout against
// the same endpoints the Angular client uses, so the backend cannot tell
// the two clients apart.
class AuthSession : public QObject
{
    Q_OBJECT
public:
    explicit AuthSession(ApiClient *api, QObject *parent = nullptr);

    QString token;
    QString username;
    int channelId = 1;
    int adminLevel = 0;
    bool loggedIn = false;

    void login(const QString &username, const QString &password, bool remember);
    void guestLogin(const QString &username);
    void tryAutoLogin();
    void logout();

signals:
    void loggedInChanged();
    void loginFailed(const QString &message);
    void loggedOut();

private:
    ApiClient *m_api;
    QSettings m_settings;

    void applyLogin(const QString &tok, const QString &user, int channel, int admin);
    void persistToken(const QString &tok);
};

#endif // AUTHSESSION_H
