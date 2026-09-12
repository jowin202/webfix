#ifndef CHATWIDGET_H
#define CHATWIDGET_H

#include <QWidget>
#include <QMap>
#include <QVector>
#include <QString>

class ApiClient;
class AuthSession;
class StreamClient;
class QComboBox;
class QTextBrowser;
class QLineEdit;
class QListWidget;
class QListWidgetItem;
class QLabel;
class QPushButton;

struct RosterUser {
    QString username;
    QString usernameHtml;
    int status = 0; // 1 = online
};

// Mirrors frontend/src/app/components/chat-window/chat-window.component:
// message stream, channel switcher, online list, whisper (click a user or
// type a name with autocomplete suggestions), /exit and /clear commands.
class ChatWidget : public QWidget
{
    Q_OBJECT
public:
    ChatWidget(ApiClient *api, AuthSession *auth, StreamClient *stream, QWidget *parent = nullptr);

    void start(); // called right after login, mirrors ngOnInit()
    void stop();  // called on logout

signals:
    void openUserMenuRequested();
    void openAdminMenuRequested();

private slots:
    void onChannelChanged(int index);
    void onSendMessage();
    void onWhisperToggle();
    void onWhisperInputChanged(const QString &value);
    void onWhisperSuggestionActivated(QListWidgetItem *item);
    void onWhisperNameConfirmed();
    void onOnlineUserActivated(QListWidgetItem *item);

    void onDefaultMessage(const QString &username, const QString &message, int channel);
    void onWhisperMessage(const QString &from, const QString &to, const QString &message);
    void onStatusMessage(const QString &message, int channel, bool hasChannel);
    void onUserPresence(bool entered, const QString &username, int channel, const QString &otherChannelName);
    void onLoginLogout(const QString &username, const QString &message);
    void onAnnouncement(const QString &message);
    void onConnectionTrouble(const QString &message);

private:
    ApiClient *m_api;
    AuthSession *m_auth;
    StreamClient *m_stream;

    QComboBox *m_channelCombo;
    QPushButton *m_menuButton;
    QPushButton *m_adminMenuButton;
    QPushButton *m_logoutButton;

    QTextBrowser *m_messagesView;

    QWidget *m_whisperChip;
    QLabel *m_whisperChipLabel;

    QLineEdit *m_messageInput;

    QListWidget *m_onlineList;
    QPushButton *m_whisperToggleButton;
    QWidget *m_whisperEntryContainer;
    QLineEdit *m_whisperNameField;
    QListWidget *m_whisperSuggestionsList;
    QLabel *m_whisperEntryError;

    QMap<QString, QString> m_htmlUsers; // username -> username_html
    QVector<RosterUser> m_allUsers;
    QString m_whisperTarget;

    void updateOnlineList();
    void updateChannelList();
    void loadAllUsers();
    void setWhisperTarget(const QString &username);
    void clearWhisperTarget();
    void closeWhisperEntry();
    void appendLine(const QString &html);
    QString displayName(const QString &username) const;
    QWidget *makeUserRow(const QString &usernameHtml, bool showDot, bool online) const;
};

#endif // CHATWIDGET_H
