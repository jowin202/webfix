#ifndef USERMENUDIALOG_H
#define USERMENUDIALOG_H

#include <QDialog>
#include <QColor>

class ApiClient;
class AuthSession;
class QLineEdit;
class QLabel;
class QPushButton;

// Mirrors frontend/src/app/components/user-menu/user-menu.component (minus
// FIDO2, which needs a platform-specific/external library and was
// deliberately left out): view/edit own profile and the username color
// gradient.
class UserMenuDialog : public QDialog
{
    Q_OBJECT
public:
    UserMenuDialog(ApiClient *api, AuthSession *auth, QWidget *parent = nullptr);

    void reload();

private:
    ApiClient *m_api;
    AuthSession *m_auth;

    QLineEdit *m_name;
    QLineEdit *m_tel;
    QLineEdit *m_mail;
    QLineEdit *m_fediverse;
    QLineEdit *m_loginMsg;
    QLineEdit *m_logoutMsg;
    QLineEdit *m_password;
    QLabel *m_message;

    QColor m_colorFrom = QColor("#ff0000");
    QColor m_colorTo = QColor("#0000ff");
    QPushButton *m_colorFromButton;
    QPushButton *m_colorToButton;

    void save();
    void applyGradient();
    void updateColorButton(QPushButton *button, const QColor &color) const;
};

#endif // USERMENUDIALOG_H
