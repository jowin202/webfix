#include "authsession.h"
#include "apiclient.h"

#include <QJsonObject>
#include <QUrlQuery>

AuthSession::AuthSession(ApiClient *api, QObject *parent)
    : QObject(parent)
    , m_api(api)
    , m_settings("Webfix", "WebfixClient")
{
}

void AuthSession::applyLogin(const QString &tok, const QString &user, int channel, int admin)
{
    token = tok;
    username = user;
    channelId = channel;
    adminLevel = admin;
    loggedIn = true;
}

void AuthSession::persistToken(const QString &tok)
{
    if (tok.isEmpty()) {
        m_settings.remove("token");
    } else {
        m_settings.setValue("token", tok);
    }
}

void AuthSession::login(const QString &user, const QString &password, bool remember)
{
    QUrlQuery form;
    form.addQueryItem("username", user);
    form.addQueryItem("password", password);
    m_api->postForm("/api/login/", form, [this, user, remember](const QJsonValue &result, int status) {
        Q_UNUSED(status)
        const QJsonObject obj = result.toObject();
        if (ApiClient::isError(result) || !obj.contains("access_token")) {
            emit loginFailed(obj.value("error_string").toString(QStringLiteral("Incorrect username or password")));
            return;
        }
        applyLogin(obj.value("access_token").toString(), user, obj.value("channel_id").toInt(1), obj.value("admin").toInt(0));
        persistToken(remember ? token : QString());
        emit loggedInChanged();
    });
}

void AuthSession::guestLogin(const QString &user)
{
    QUrlQuery q;
    q.addQueryItem("username", user);
    // The web client hardcodes remember=false for guest logins.
    m_api->postQuery("/api/login/guest_login/", QString(), q, [this, user](const QJsonValue &result, int status) {
        Q_UNUSED(status)
        const QJsonObject obj = result.toObject();
        if (ApiClient::isError(result) || !obj.contains("access_token")) {
            emit loginFailed(obj.value("error_string").toString(QStringLiteral("Guest Login Error")));
            return;
        }
        applyLogin(obj.value("access_token").toString(), user, obj.value("channel_id").toInt(1), 0);
        emit loggedInChanged();
    });
}

void AuthSession::tryAutoLogin()
{
    const QString stored = m_settings.value("token").toString();
    if (stored.isEmpty()) {
        return;
    }
    m_api->get(QString("/api/login/from_token/%1/").arg(stored), stored, [this, stored](const QJsonValue &result, int status) {
        Q_UNUSED(status)
        const QJsonObject obj = result.toObject();
        if (ApiClient::isError(result) || !obj.contains("username")) {
            persistToken(QString()); // stale/invalid stored token
            return;
        }
        applyLogin(stored, obj.value("username").toString(), obj.value("channel_id").toInt(1), obj.value("admin").toInt(0));
        emit loggedInChanged();
    });
}

void AuthSession::logout()
{
    if (!token.isEmpty()) {
        const QString tok = token;
        m_api->get(QString("/api/login/logout_token/%1/").arg(tok), QString(), [](const QJsonValue &, int) {});
    }
    persistToken(QString());
    token.clear();
    username.clear();
    channelId = 1;
    adminLevel = 0;
    loggedIn = false;
    emit loggedOut();
}
