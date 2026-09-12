#include "apiclient.h"

#include <QJsonDocument>
#include <QJsonArray>
#include <QUrl>

ApiClient::ApiClient(QObject *parent)
    : QObject(parent)
    , m_nam(new QNetworkAccessManager(this))
    , m_serverUrl("http://localhost:8000")
{
}

QString ApiClient::wsUrl() const
{
    if (m_serverUrl.startsWith("https://")) {
        return "wss://" + m_serverUrl.mid(8);
    }
    if (m_serverUrl.startsWith("http://")) {
        return "ws://" + m_serverUrl.mid(7);
    }
    return "ws://" + m_serverUrl;
}

QNetworkRequest ApiClient::makeRequest(const QString &path, const QString &token, const QString &contentType) const
{
    QNetworkRequest req(QUrl(m_serverUrl + path));
    if (!token.isEmpty()) {
        req.setRawHeader("Authorization", "Bearer " + token.toUtf8());
    }
    if (!contentType.isEmpty()) {
        req.setHeader(QNetworkRequest::ContentTypeHeader, contentType);
    }
    return req;
}

void ApiClient::finish(QNetworkReply *reply, Callback cb)
{
    connect(reply, &QNetworkReply::finished, this, [reply, cb]() {
        reply->deleteLater();
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray data = reply->readAll();

        if (status == 0) {
            // Transport-level failure: server unreachable, no HTTP response at all.
            cb(QJsonObject{{"error_code", -1}, {"error_string", reply->errorString()}}, 0);
            return;
        }

        QJsonParseError parseError;
        const QJsonDocument doc = QJsonDocument::fromJson(data, &parseError);

        if (status >= 400) {
            QString detail = (parseError.error == QJsonParseError::NoError)
                                  ? doc.object().value("detail").toString()
                                  : QString();
            cb(QJsonObject{{"error_code", status},
                            {"error_string", detail.isEmpty() ? QStringLiteral("Request failed") : detail}},
               status);
            return;
        }

        if (parseError.error != QJsonParseError::NoError) {
            cb(QJsonObject{{"error_code", -1}, {"error_string", "no valid json"}}, status);
            return;
        }

        cb(doc.isArray() ? QJsonValue(doc.array()) : QJsonValue(doc.object()), status);
    });
}

void ApiClient::get(const QString &path, const QString &token, Callback cb)
{
    finish(m_nam->get(makeRequest(path, token)), cb);
}

void ApiClient::postJson(const QString &path, const QString &token, const QJsonObject &body, Callback cb)
{
    postJsonDoc(path, token, QJsonDocument(body), cb);
}

void ApiClient::postJsonDoc(const QString &path, const QString &token, const QJsonDocument &doc, Callback cb)
{
    QNetworkRequest req = makeRequest(path, token, "application/json");
    finish(m_nam->post(req, doc.toJson(QJsonDocument::Compact)), cb);
}

void ApiClient::postForm(const QString &path, const QUrlQuery &formFields, Callback cb)
{
    QNetworkRequest req = makeRequest(path, QString(), "application/x-www-form-urlencoded");
    finish(m_nam->post(req, formFields.query(QUrl::FullyEncoded).toUtf8()), cb);
}

void ApiClient::postQuery(const QString &path, const QString &token, const QUrlQuery &queryParams, Callback cb)
{
    QUrl url(m_serverUrl + path);
    url.setQuery(queryParams);
    QNetworkRequest req(url);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/octet-stream");
    if (!token.isEmpty()) {
        req.setRawHeader("Authorization", "Bearer " + token.toUtf8());
    }
    finish(m_nam->post(req, QByteArray()), cb);
}

void ApiClient::putJson(const QString &path, const QString &token, const QJsonObject &body, Callback cb)
{
    QNetworkRequest req = makeRequest(path, token, "application/json");
    finish(m_nam->put(req, QJsonDocument(body).toJson(QJsonDocument::Compact)), cb);
}

void ApiClient::del(const QString &path, const QString &token, Callback cb)
{
    finish(m_nam->deleteResource(makeRequest(path, token)), cb);
}

bool ApiClient::isError(const QJsonValue &value)
{
    return value.isObject() && value.toObject().contains("error_code");
}
