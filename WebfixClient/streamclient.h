#ifndef STREAMCLIENT_H
#define STREAMCLIENT_H

#include <QObject>
#include <QString>

class QWebSocket;
class QTimer;
class ApiClient;

// Mirrors frontend/src/app/services/stream.service.ts and the WebSocket
// part of api.service.ts: one connection bound to exactly one channel at a
// time. Switching channels tears the old connection down and opens a new
// one, sending a "switch_leave" control frame on the old socket first so
// the backend announces "left the channel (to Y)" there instead of a plain
// leave notice, exactly like the Angular client does.
class StreamClient : public QObject
{
    Q_OBJECT
public:
    explicit StreamClient(ApiClient *api, QObject *parent = nullptr);

    // fromChannelId = -1 means "not a switch" (initial connect / manual reconnect).
    void connectToChannel(const QString &token, int channelId, bool announce, int fromChannelId = -1);
    void disconnectStream();

signals:
    void defaultMessage(const QString &username, const QString &message, int channel);
    void whisperMessage(const QString &from, const QString &to, const QString &message);
    void statusMessage(const QString &message, int channel, bool hasChannel);
    void userPresence(bool entered, const QString &username, int channel, const QString &otherChannelName);
    void loginLogout(const QString &username, const QString &message);
    void announcement(const QString &message);
    void connectionTrouble(const QString &message);

private:
    ApiClient *m_api;
    QWebSocket *m_socket = nullptr;
    QTimer *m_reconnectTimer;
    QString m_token;
    int m_channelId = 1;
    bool m_announce = true;
    bool m_manuallyClosed = false;

    void closeCurrentSocket();
    void openSocket(int fromChannelId);
    void handleTextMessage(const QString &text);
};

#endif // STREAMCLIENT_H
