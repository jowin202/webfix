#include "loginwidget.h"
#include "apiclient.h"
#include "authsession.h"

#include <QVBoxLayout>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QLineEdit>
#include <QCheckBox>
#include <QLabel>
#include <QPushButton>
#include <QGroupBox>
#include <QJsonObject>
#include <QJsonArray>
#include <QFrame>

LoginWidget::LoginWidget(ApiClient *api, AuthSession *auth, QWidget *parent)
    : QWidget(parent)
    , m_api(api)
    , m_auth(auth)
{
    auto *root = new QVBoxLayout(this);
    root->setAlignment(Qt::AlignTop);

    auto *title = new QLabel(QStringLiteral("Webfix Chat"));
    QFont titleFont = title->font();
    titleFont.setPointSize(titleFont.pointSize() + 6);
    titleFont.setBold(true);
    title->setFont(titleFont);
    root->addWidget(title);

    auto *form = new QFormLayout();
    m_username = new QLineEdit();
    m_password = new QLineEdit();
    m_password->setEchoMode(QLineEdit::Password);
    form->addRow(QStringLiteral("Username:"), m_username);
    form->addRow(QStringLiteral("Password:"), m_password);
    root->addLayout(form);

    m_remember = new QCheckBox(QStringLiteral("Remember me"));
    root->addWidget(m_remember);

    m_error = new QLabel();
    m_error->setStyleSheet("color: red;");
    m_error->hide();
    root->addWidget(m_error);

    m_loginButton = new QPushButton(QStringLiteral("Login"));
    root->addWidget(m_loginButton);

    auto *linksRow = new QHBoxLayout();
    auto *registerLink = new QPushButton(QStringLiteral("Register"));
    registerLink->setFlat(true);
    auto *forgotLink = new QPushButton(QStringLiteral("Forgot password?"));
    forgotLink->setFlat(true);
    linksRow->addWidget(registerLink);
    linksRow->addWidget(forgotLink);
    root->addLayout(linksRow);

    auto *sep = new QFrame();
    sep->setFrameShape(QFrame::HLine);
    root->addWidget(sep);

    m_guestBox = new QGroupBox(QStringLiteral("Guest login"));
    auto *guestLayout = new QVBoxLayout(m_guestBox);
    m_guestUsername = new QLineEdit();
    m_guestUsername->setPlaceholderText(QStringLiteral("Guest username (min. 4 characters)"));
    guestLayout->addWidget(m_guestUsername);
    m_guestError = new QLabel();
    m_guestError->setStyleSheet("color: red;");
    m_guestError->hide();
    guestLayout->addWidget(m_guestError);
    m_guestLoginButton = new QPushButton(QStringLiteral("Join as guest"));
    guestLayout->addWidget(m_guestLoginButton);
    root->addWidget(m_guestBox);
    m_guestBox->hide();

    m_onlineCountLabel = new QLabel();
    root->addWidget(m_onlineCountLabel);

    connect(m_loginButton, &QPushButton::clicked, this, &LoginWidget::doLogin);
    connect(m_password, &QLineEdit::returnPressed, this, &LoginWidget::doLogin);
    connect(m_guestLoginButton, &QPushButton::clicked, this, &LoginWidget::doGuestLogin);
    connect(m_guestUsername, &QLineEdit::returnPressed, this, &LoginWidget::doGuestLogin);
    connect(registerLink, &QPushButton::clicked, this, &LoginWidget::registerRequested);
    connect(forgotLink, &QPushButton::clicked, this, &LoginWidget::forgotPasswordRequested);

    connect(m_auth, &AuthSession::loginFailed, this, [this](const QString &message) {
        if (message.isEmpty()) {
            return;
        }
        m_error->setText(message);
        m_error->show();
        m_guestError->setText(message);
        m_guestError->show();
    });
}

void LoginWidget::refreshPublicInfo()
{
    m_error->hide();
    m_guestError->hide();
    m_password->clear();

    m_api->get("/api/register/public_infos/", QString(), [this](const QJsonValue &result, int) {
        if (ApiClient::isError(result)) {
            return;
        }
        const QJsonObject obj = result.toObject();
        m_guestBox->setVisible(obj.value("allow_guest_login").toBool());
        const int numUsers = obj.value("num_users").toInt();
        m_onlineCountLabel->setText(QStringLiteral("%1 user(s) online").arg(numUsers));
    });
}

void LoginWidget::doLogin()
{
    m_error->hide();
    if (m_username->text().isEmpty() || m_password->text().isEmpty()) {
        return;
    }
    m_auth->login(m_username->text(), m_password->text(), m_remember->isChecked());
}

void LoginWidget::doGuestLogin()
{
    m_guestError->hide();
    if (m_guestUsername->text().isEmpty()) {
        return;
    }
    m_auth->guestLogin(m_guestUsername->text());
}
