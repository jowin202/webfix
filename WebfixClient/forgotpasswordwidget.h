#ifndef FORGOTPASSWORDWIDGET_H
#define FORGOTPASSWORDWIDGET_H

#include <QWidget>

class ApiClient;
class QLineEdit;
class QLabel;
class QPushButton;

// Mirrors forgot-password.component.ts + recover-password.component.ts.
// Since a desktop app has no URL routing for the emailed recovery link,
// the recovery token is entered manually (copy-pasted from the mail/toot).
class ForgotPasswordWidget : public QWidget
{
    Q_OBJECT
public:
    explicit ForgotPasswordWidget(ApiClient *api, QWidget *parent = nullptr);

    void reset();

signals:
    void backToLoginRequested();

private:
    ApiClient *m_api;

    QLineEdit *m_username;
    QLineEdit *m_mail;
    QLineEdit *m_fediverse;
    QLabel *m_requestMessage;
    QPushButton *m_requestButton;

    QLineEdit *m_recoveryToken;
    QLineEdit *m_newPassword;
    QLabel *m_recoverMessage;
    QPushButton *m_recoverButton;

    void doRequest();
    void doRecover();
};

#endif // FORGOTPASSWORDWIDGET_H
