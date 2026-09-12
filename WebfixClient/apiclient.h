#ifndef APICLIENT_H
#define APICLIENT_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QJsonValue>
#include <QJsonObject>
#include <QJsonDocument>
#include <QUrlQuery>
#include <functional>

// Thin REST wrapper mirroring frontend/src/app/services/api.service.ts:
// every call resolves via callback with a QJsonValue (object or array).
// Network/HTTP failures resolve as {"error_code": ..., "error_string": ...}
// so callers can check for that key the same way the Angular client does,
// instead of throwing.
class ApiClient : public QObject
{
    Q_OBJECT
public:
    using Callback = std::function<void(const QJsonValue &result, int httpStatus)>;

    explicit ApiClient(QObject *parent = nullptr);

    QString serverUrl() const { return m_serverUrl; }
    void setServerUrl(const QString &url) { m_serverUrl = url; }
    QString wsUrl() const;

    void get(const QString &path, const QString &token, Callback cb);
    void postJson(const QString &path, const QString &token, const QJsonObject &body, Callback cb);
    // For the handful of endpoints that take a raw JSON array body (e.g.
    // POST /api/admin/settings/get_settings/) rather than an object.
    void postJsonDoc(const QString &path, const QString &token, const QJsonDocument &doc, Callback cb);
    void postForm(const QString &path, const QUrlQuery &formFields, Callback cb);
    void postQuery(const QString &path, const QString &token, const QUrlQuery &queryParams, Callback cb);
    void putJson(const QString &path, const QString &token, const QJsonObject &body, Callback cb);
    void del(const QString &path, const QString &token, Callback cb);

    static bool isError(const QJsonValue &value);

private:
    QNetworkAccessManager *m_nam;
    QString m_serverUrl;

    QNetworkRequest makeRequest(const QString &path, const QString &token,
                                const QString &contentType = QString()) const;
    void finish(QNetworkReply *reply, Callback cb);
};

#endif // APICLIENT_H
