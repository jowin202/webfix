#include "streamclient.h"
#include "apiclient.h"

#include <QWebSocket>
#include <QTimer>
#include <QJsonDocument>
#include <QJsonObject>
#include <QUrl>
#include <QUrlQuery>

StreamClient::StreamClient(ApiClient *api, QObject *parent)
    : QObject(parent)
    , m_api(api)
    , m_reconnectTimer(new QTimer(this))
{
    m_reconnectTimer->setSingleShot(true);
    m_reconnectTimer->setInterval(5000);
    connect(m_reconnectTimer, &QTimer::timeout, this, [this]() { openSocket(-1); });
}

void StreamClient::connectToChannel(const QString &token, int channelId, bool announce, int fromChannelId)
{
    m_reconnectTimer->stop();

    if (fromChannelId >= 0 && m_socket) {
        const QJsonObject leave{{"action", "switch_leave"}, {"to_channel_id", channelId}};
        m_socket->sendTextMessage(QString::fromUtf8(QJsonDocument(leave).toJson(QJsonDocument::Compact)));
    }

    closeCurrentSocket();

    m_token = token;
    m_channelId = channelId;
    m_announce = announce;
    m_manuallyClosed = false;
    openSocket(fromChannelId);
}

void StreamClient::disconnectStream()
{
    m_reconnectTimer->stop();
    closeCurrentSocket();
}

void StreamClient::closeCurrentSocket()
{
    if (!m_socket) {
        return;
    }
    m_manuallyClosed = true;
    QWebSocket *s = m_socket;
    m_socket = nullptr;
    s->disconnect(this);
    s->close();
    s->deleteLater();
}

void StreamClient::openSocket(int fromChannelId)
{
    QUrl url(m_api->wsUrl() + "/api/stream/ws");
    QUrlQuery q;
    q.addQueryItem("channel_id", QString::number(m_channelId));
    q.addQueryItem("announce", m_announce ? "1" : "0");
    if (fromChannelId >= 0) {
        q.addQueryItem("from_channel_id", QString::number(fromChannelId));
    }
    q.addQueryItem("token", m_token);
    url.setQuery(q);

    m_manuallyClosed = false;
    m_socket = new QWebSocket();

    connect(m_socket, &QWebSocket::textMessageReceived, this, &StreamClient::handleTextMessage);
    connect(m_socket, &QWebSocket::disconnected, this, [this]() {
        if (!m_manuallyClosed) {
            emit connectionTrouble(QStringLiteral("WebSocket closed unexpectedly; retrying in 5s"));
            m_reconnectTimer->start();
        }
    });

    m_socket->open(url);
}

void StreamClient::handleTextMessage(const QString &text)
{
    const QJsonDocument doc = QJsonDocument::fromJson(text.toUtf8());
    if (!doc.isObject()) {
        return; // mirrors the Angular client silently dropping non-JSON frames
    }
    const QJsonObject obj = doc.object();

    if (obj.contains("username") && obj.contains("message") && !obj.contains("toUser")) {
        emit defaultMessage(obj.value("username").toString(), obj.value("message").toString(),
                             obj.contains("channel") ? obj.value("channel").toInt() : m_channelId);
        return;
    }

    const QString cat = obj.value("cat").toString();

    if (cat == QLatin1String("whisper") && obj.contains("from") && obj.contains("msg")) {
        emit whisperMessage(obj.value("from").toString(), obj.value("to").toString(), obj.value("msg").toString());
        return;
    }

    if (cat == QLatin1String("statusmsg")) {
        const bool hasChannel = obj.contains("channel");
        emit statusMessage(obj.value("msg").toString(), hasChannel ? obj.value("channel").toInt() : -1, hasChannel);
        return;
    }

    if (cat == QLatin1String("userenters") || cat == QLatin1String("userleft")) {
        emit userPresence(cat == QLatin1String("userenters"), obj.value("username").toString(),
                           obj.value("channel").toInt(), obj.value("other_channel_name").toString());
        return;
    }

    if (cat == QLatin1String("userlogin") || cat == QLatin1String("userlogout")) {
        emit loginLogout(obj.value("username").toString(), obj.value("msg").toString());
        return;
    }

    if (cat == QLatin1String("announcement")) {
        emit announcement(obj.value("msg").toString());
        return;
    }
}
