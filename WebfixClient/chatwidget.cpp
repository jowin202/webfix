#include "chatwidget.h"
#include "apiclient.h"
#include "authsession.h"
#include "streamclient.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QComboBox>
#include <QTextBrowser>
#include <QScrollBar>
#include <QLineEdit>
#include <QListWidget>
#include <QLabel>
#include <QPushButton>
#include <QJsonArray>
#include <QJsonObject>
#include <QUrlQuery>
#include <QFont>

ChatWidget::ChatWidget(ApiClient *api, AuthSession *auth, StreamClient *stream, QWidget *parent)
    : QWidget(parent)
    , m_api(api)
    , m_auth(auth)
    , m_stream(stream)
{
    auto *root = new QVBoxLayout(this);

    auto *topRow = new QHBoxLayout();
    topRow->addWidget(new QLabel(QStringLiteral("Channel:")));
    m_channelCombo = new QComboBox();
    topRow->addWidget(m_channelCombo);
    topRow->addStretch();
    m_menuButton = new QPushButton(QStringLiteral("Menu"));
    m_adminMenuButton = new QPushButton(QStringLiteral("Admin Menu"));
    m_logoutButton = new QPushButton(QStringLiteral("Logout"));
    topRow->addWidget(m_menuButton);
    topRow->addWidget(m_adminMenuButton);
    topRow->addWidget(m_logoutButton);
    root->addLayout(topRow);

    auto *middleRow = new QHBoxLayout();

    auto *chatColumn = new QVBoxLayout();
    m_messagesView = new QTextBrowser();
    m_messagesView->setOpenExternalLinks(false);
    chatColumn->addWidget(m_messagesView, 1);

    m_whisperChip = new QWidget();
    auto *chipLayout = new QHBoxLayout(m_whisperChip);
    chipLayout->setContentsMargins(0, 0, 0, 0);
    chipLayout->addWidget(new QLabel(QStringLiteral("Whisper to:")));
    m_whisperChipLabel = new QLabel();
    chipLayout->addWidget(m_whisperChipLabel);
    auto *chipClose = new QPushButton(QStringLiteral("×"));
    chipClose->setFixedWidth(24);
    chipLayout->addWidget(chipClose);
    chipLayout->addStretch();
    m_whisperChip->hide();
    chatColumn->addWidget(m_whisperChip);

    m_messageInput = new QLineEdit();
    m_messageInput->setPlaceholderText(QStringLiteral("Message ..."));
    chatColumn->addWidget(m_messageInput);

    middleRow->addLayout(chatColumn, 3);

    auto *sidebarColumn = new QVBoxLayout();
    auto *onlineHeaderRow = new QHBoxLayout();
    onlineHeaderRow->addWidget(new QLabel(QStringLiteral("Online")));
    m_whisperToggleButton = new QPushButton(QStringLiteral("Whisper"));
    onlineHeaderRow->addWidget(m_whisperToggleButton);
    sidebarColumn->addLayout(onlineHeaderRow);

    m_whisperEntryContainer = new QWidget();
    auto *whisperEntryLayout = new QVBoxLayout(m_whisperEntryContainer);
    whisperEntryLayout->setContentsMargins(0, 0, 0, 0);
    m_whisperNameField = new QLineEdit();
    m_whisperNameField->setPlaceholderText(QStringLiteral("Username ..."));
    whisperEntryLayout->addWidget(m_whisperNameField);
    m_whisperSuggestionsList = new QListWidget();
    m_whisperSuggestionsList->setMaximumHeight(120);
    whisperEntryLayout->addWidget(m_whisperSuggestionsList);
    m_whisperEntryError = new QLabel();
    m_whisperEntryError->setStyleSheet("color: red;");
    m_whisperEntryError->setWordWrap(true);
    m_whisperEntryError->hide();
    whisperEntryLayout->addWidget(m_whisperEntryError);
    m_whisperEntryContainer->hide();
    sidebarColumn->addWidget(m_whisperEntryContainer);

    m_onlineList = new QListWidget();
    sidebarColumn->addWidget(m_onlineList, 1);

    middleRow->addLayout(sidebarColumn, 1);
    root->addLayout(middleRow, 1);

    connect(m_channelCombo, QOverload<int>::of(&QComboBox::activated), this, &ChatWidget::onChannelChanged);
    connect(m_messageInput, &QLineEdit::returnPressed, this, &ChatWidget::onSendMessage);
    connect(chipClose, &QPushButton::clicked, this, &ChatWidget::clearWhisperTarget);
    connect(m_whisperToggleButton, &QPushButton::clicked, this, &ChatWidget::onWhisperToggle);
    connect(m_whisperNameField, &QLineEdit::textChanged, this, &ChatWidget::onWhisperInputChanged);
    connect(m_whisperNameField, &QLineEdit::returnPressed, this, &ChatWidget::onWhisperNameConfirmed);
    connect(m_whisperSuggestionsList, &QListWidget::itemClicked, this, &ChatWidget::onWhisperSuggestionActivated);
    connect(m_onlineList, &QListWidget::itemClicked, this, &ChatWidget::onOnlineUserActivated);
    connect(m_menuButton, &QPushButton::clicked, this, &ChatWidget::openUserMenuRequested);
    connect(m_adminMenuButton, &QPushButton::clicked, this, &ChatWidget::openAdminMenuRequested);
    connect(m_logoutButton, &QPushButton::clicked, this, [this]() { m_auth->logout(); });

    connect(m_stream, &StreamClient::defaultMessage, this, &ChatWidget::onDefaultMessage);
    connect(m_stream, &StreamClient::whisperMessage, this, &ChatWidget::onWhisperMessage);
    connect(m_stream, &StreamClient::statusMessage, this, &ChatWidget::onStatusMessage);
    connect(m_stream, &StreamClient::userPresence, this, &ChatWidget::onUserPresence);
    connect(m_stream, &StreamClient::loginLogout, this, &ChatWidget::onLoginLogout);
    connect(m_stream, &StreamClient::announcement, this, &ChatWidget::onAnnouncement);
    connect(m_stream, &StreamClient::connectionTrouble, this, &ChatWidget::onConnectionTrouble);
}

void ChatWidget::start()
{
    m_messagesView->clear();
    m_htmlUsers.clear();
    m_allUsers.clear();
    clearWhisperTarget();
    closeWhisperEntry();

    m_adminMenuButton->setVisible(m_auth->adminLevel >= 3);

    m_stream->connectToChannel(m_auth->token, m_auth->channelId, true);
    updateOnlineList();
    updateChannelList();
}

void ChatWidget::stop()
{
    m_stream->disconnectStream();
}

void ChatWidget::updateOnlineList()
{
    m_api->get(QString("/api/data/users_by_channel_id/%1/").arg(m_auth->channelId), m_auth->token,
               [this](const QJsonValue &result, int) {
        if (ApiClient::isError(result) || !result.isArray()) {
            return;
        }
        m_onlineList->clear();
        for (const QJsonValue &v : result.toArray()) {
            const QJsonObject obj = v.toObject();
            const QString username = obj.value("username").toString();
            const QString html = obj.value("username_html").toString(username);
            m_htmlUsers[username] = html;

            auto *item = new QListWidgetItem();
            item->setData(Qt::UserRole, username);
            m_onlineList->addItem(item);
            m_onlineList->setItemWidget(item, makeUserRow(html, false, true));
        }
    });
}

void ChatWidget::updateChannelList()
{
    m_api->get("/api/data/channels/", m_auth->token, [this](const QJsonValue &result, int) {
        if (ApiClient::isError(result) || !result.isArray()) {
            return;
        }
        m_channelCombo->blockSignals(true);
        m_channelCombo->clear();
        for (const QJsonValue &v : result.toArray()) {
            const QJsonObject obj = v.toObject();
            m_channelCombo->addItem(obj.value("name").toString(), obj.value("id").toInt());
        }
        const int idx = m_channelCombo->findData(m_auth->channelId);
        if (idx >= 0) {
            m_channelCombo->setCurrentIndex(idx);
        }
        m_channelCombo->blockSignals(false);
    });
}

void ChatWidget::loadAllUsers()
{
    m_api->get("/api/data/users/", m_auth->token, [this](const QJsonValue &result, int) {
        if (ApiClient::isError(result) || !result.isArray()) {
            return;
        }
        m_allUsers.clear();
        for (const QJsonValue &v : result.toArray()) {
            const QJsonObject obj = v.toObject();
            RosterUser u;
            u.username = obj.value("username").toString();
            u.usernameHtml = obj.value("username_html").toString(u.username);
            u.status = obj.value("status").toInt();
            m_allUsers.append(u);
        }
    });
}

void ChatWidget::onChannelChanged(int index)
{
    const int toChannelId = m_channelCombo->itemData(index).toInt();
    const int fromChannelId = m_auth->channelId;
    if (toChannelId == fromChannelId) {
        return;
    }

    m_auth->channelId = toChannelId;
    m_stream->connectToChannel(m_auth->token, toChannelId, false, fromChannelId);

    const QJsonObject body{{"from_channel_id", fromChannelId}, {"to_channel_id", toChannelId}};
    m_api->postJson("/api/channels/switch/", m_auth->token, body, [](const QJsonValue &, int) {});

    updateOnlineList();
}

void ChatWidget::onSendMessage()
{
    const QString text = m_messageInput->text();
    if (text.isEmpty()) {
        return;
    }
    m_messageInput->clear();

    if (text == QLatin1String("/exit")) {
        m_auth->logout();
        return;
    }
    if (text == QLatin1String("/clear")) {
        m_messagesView->clear();
        return;
    }

    if (!m_whisperTarget.isEmpty()) {
        QUrlQuery q;
        q.addQueryItem("to_username", m_whisperTarget);
        q.addQueryItem("message", text);
        m_api->postQuery("/api/input/wh", m_auth->token, q, [](const QJsonValue &, int) {});
        clearWhisperTarget(); // whisper mode is one-shot, matching the web client
        return;
    }

    const QJsonObject body{{"message", text}, {"channel_id", m_auth->channelId}};
    m_api->postJson("/api/input/", m_auth->token, body, [](const QJsonValue &, int) {});
}

void ChatWidget::onWhisperToggle()
{
    if (m_whisperEntryContainer->isVisible()) {
        closeWhisperEntry();
        m_messageInput->setFocus();
    } else {
        loadAllUsers();
        m_whisperEntryContainer->show();
        m_whisperNameField->setFocus();
    }
}

void ChatWidget::onWhisperInputChanged(const QString &value)
{
    m_whisperSuggestionsList->clear();
    m_whisperEntryError->hide();

    const QString needle = value.trimmed().toLower();
    if (needle.isEmpty()) {
        return;
    }

    int count = 0;
    for (const RosterUser &u : m_allUsers) {
        if (count >= 8) {
            break;
        }
        if (!u.username.toLower().contains(needle)) {
            continue;
        }
        auto *item = new QListWidgetItem();
        item->setData(Qt::UserRole, u.username);
        m_whisperSuggestionsList->addItem(item);
        m_whisperSuggestionsList->setItemWidget(item, makeUserRow(u.usernameHtml, true, u.status == 1));
        ++count;
    }
}

void ChatWidget::onWhisperSuggestionActivated(QListWidgetItem *item)
{
    if (!item) {
        return;
    }
    setWhisperTarget(item->data(Qt::UserRole).toString());
    closeWhisperEntry();
}

void ChatWidget::onWhisperNameConfirmed()
{
    const QString typed = m_whisperNameField->text().trimmed();
    if (typed.isEmpty()) {
        closeWhisperEntry();
        return;
    }

    for (const RosterUser &u : m_allUsers) {
        if (u.username.compare(typed, Qt::CaseInsensitive) == 0) {
            setWhisperTarget(u.username);
            closeWhisperEntry();
            return;
        }
    }

    m_whisperEntryError->setText(QString("User \"%1\" not found.").arg(typed));
    m_whisperEntryError->show();
    m_whisperSuggestionsList->clear();
}

void ChatWidget::onOnlineUserActivated(QListWidgetItem *item)
{
    if (!item) {
        return;
    }
    setWhisperTarget(item->data(Qt::UserRole).toString());
}

void ChatWidget::setWhisperTarget(const QString &username)
{
    m_whisperTarget = username;
    m_whisperChipLabel->setText(username);
    m_whisperChip->show();
    m_messageInput->setFocus();
}

void ChatWidget::clearWhisperTarget()
{
    m_whisperTarget.clear();
    m_whisperChip->hide();
}

void ChatWidget::closeWhisperEntry()
{
    m_whisperEntryContainer->hide();
    m_whisperNameField->clear();
    m_whisperSuggestionsList->clear();
    m_whisperEntryError->hide();
}

void ChatWidget::appendLine(const QString &html)
{
    m_messagesView->append(html);
    QScrollBar *bar = m_messagesView->verticalScrollBar();
    bar->setValue(bar->maximum());
}

QString ChatWidget::displayName(const QString &username) const
{
    return m_htmlUsers.value(username, username);
}

QWidget *ChatWidget::makeUserRow(const QString &usernameHtml, bool showDot, bool online) const
{
    auto *w = new QWidget();
    auto *l = new QHBoxLayout(w);
    l->setContentsMargins(4, 2, 4, 2);
    if (showDot) {
        auto *dot = new QLabel();
        dot->setFixedSize(8, 8);
        dot->setStyleSheet(QString("background-color: %1; border-radius: 4px;").arg(online ? "limegreen" : "gray"));
        l->addWidget(dot);
    }
    auto *label = new QLabel();
    label->setTextFormat(Qt::RichText);
    label->setText(usernameHtml);
    l->addWidget(label);
    l->addStretch();
    return w;
}

void ChatWidget::onDefaultMessage(const QString &username, const QString &message, int channel)
{
    Q_UNUSED(channel) // this connection only ever carries the channel we're bound to
    appendLine(QString("%1: %2").arg(displayName(username), message));
}

void ChatWidget::onWhisperMessage(const QString &from, const QString &to, const QString &message)
{
    if (from == m_auth->username) {
        appendLine(QString("<i>Whisper to</i> %1: %2").arg(displayName(to), message));
    } else {
        appendLine(QString("%1 <i>whispers</i>: %2").arg(displayName(from), message));
    }
}

void ChatWidget::onStatusMessage(const QString &message, int channel, bool hasChannel)
{
    Q_UNUSED(channel)
    Q_UNUSED(hasChannel)
    appendLine(QString("<i>%1</i>").arg(message));
}

void ChatWidget::onUserPresence(bool entered, const QString &username, int channel, const QString &otherChannelName)
{
    Q_UNUSED(channel)
    const QString name = displayName(username);
    QString text;
    if (entered) {
        text = otherChannelName.isEmpty() ? QString("%1 joined the channel").arg(name)
                                           : QString("%1 joined the channel (from %2)").arg(name, otherChannelName);
    } else {
        text = otherChannelName.isEmpty() ? QString("%1 left the channel").arg(name)
                                           : QString("%1 left the channel (to %2)").arg(name, otherChannelName);
    }
    appendLine(QString("<i>%1</i>").arg(text));
    updateOnlineList();
}

void ChatWidget::onLoginLogout(const QString &username, const QString &message)
{
    appendLine(QString("<i>%1 %2</i>").arg(displayName(username), message));
    updateOnlineList();
}

void ChatWidget::onAnnouncement(const QString &message)
{
    appendLine(message);
}

void ChatWidget::onConnectionTrouble(const QString &message)
{
    appendLine(QString("<font color='red'>%1</font>").arg(message));
}
