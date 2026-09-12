#include "forgotpasswordwidget.h"
#include "apiclient.h"

#include <QVBoxLayout>
#include <QFormLayout>
#include <QLineEdit>
#include <QLabel>
#include <QPushButton>
#include <QGroupBox>
#include <QJsonObject>

ForgotPasswordWidget::ForgotPasswordWidget(ApiClient *api, QWidget *parent)
    : QWidget(parent)
    , m_api(api)
{
    auto *root = new QVBoxLayout(this);
    root->setAlignment(Qt::AlignTop);

    auto *title = new QLabel(QStringLiteral("Forgot password"));
    QFont titleFont = title->font();
    titleFont.setPointSize(titleFont.pointSize() + 4);
    titleFont.setBold(true);
    title->setFont(titleFont);
    root->addWidget(title);

    auto *requestBox = new QGroupBox(QStringLiteral("Request a reset link"));
    auto *requestForm = new QFormLayout(requestBox);
    m_username = new QLineEdit();
    m_mail = new QLineEdit();
    m_fediverse = new QLineEdit();
    requestForm->addRow(QStringLiteral("Username:"), m_username);
    requestForm->addRow(QStringLiteral("E-mail:"), m_mail);
    requestForm->addRow(QStringLiteral("Fediverse ID:"), m_fediverse);
    m_requestMessage = new QLabel();
    m_requestMessage->setWordWrap(true);
    m_requestMessage->hide();
    requestForm->addRow(m_requestMessage);
    m_requestButton = new QPushButton(QStringLiteral("Send reset link"));
    requestForm->addRow(m_requestButton);
    root->addWidget(requestBox);

    auto *recoverBox = new QGroupBox(QStringLiteral("Have a reset token?"));
    auto *recoverForm = new QFormLayout(recoverBox);
    m_recoveryToken = new QLineEdit();
    m_recoveryToken->setPlaceholderText(QStringLiteral("Paste the token from the reset link"));
    m_newPassword = new QLineEdit();
    m_newPassword->setEchoMode(QLineEdit::Password);
    recoverForm->addRow(QStringLiteral("Reset token:"), m_recoveryToken);
    recoverForm->addRow(QStringLiteral("New password:"), m_newPassword);
    m_recoverMessage = new QLabel();
    m_recoverMessage->setWordWrap(true);
    m_recoverMessage->hide();
    recoverForm->addRow(m_recoverMessage);
    m_recoverButton = new QPushButton(QStringLiteral("Set new password"));
    recoverForm->addRow(m_recoverButton);
    root->addWidget(recoverBox);

    auto *backButton = new QPushButton(QStringLiteral("Back to login"));
    backButton->setFlat(true);
    root->addWidget(backButton);

    connect(m_requestButton, &QPushButton::clicked, this, &ForgotPasswordWidget::doRequest);
    connect(m_recoverButton, &QPushButton::clicked, this, &ForgotPasswordWidget::doRecover);
    connect(backButton, &QPushButton::clicked, this, &ForgotPasswordWidget::backToLoginRequested);
}

void ForgotPasswordWidget::reset()
{
    m_username->clear();
    m_mail->clear();
    m_fediverse->clear();
    m_requestMessage->hide();
    m_recoveryToken->clear();
    m_newPassword->clear();
    m_recoverMessage->hide();
}

void ForgotPasswordWidget::doRequest()
{
    m_requestMessage->hide();
    if (m_username->text().isEmpty() || (m_mail->text().isEmpty() && m_fediverse->text().isEmpty())) {
        m_requestMessage->setStyleSheet("color: red;");
        m_requestMessage->setText(QStringLiteral("Enter your username and either an e-mail or fediverse ID."));
        m_requestMessage->show();
        return;
    }

    // Matches the web client: mail and fediverse requests are independent,
    // both fire if both fields are filled in.
    if (!m_mail->text().isEmpty()) {
        const QJsonObject body{{"username", m_username->text()}, {"mail", m_mail->text()}};
        m_api->postJson("/api/pwmanage/lost_password_mail/", QString(), body, [](const QJsonValue &, int) {});
    }
    if (!m_fediverse->text().isEmpty()) {
        const QJsonObject body{{"username", m_username->text()}, {"fediverse_id", m_fediverse->text()}};
        m_api->postJson("/api/pwmanage/lost_password_fediverse/", QString(), body, [](const QJsonValue &, int) {});
    }

    m_requestMessage->setStyleSheet("color: green;");
    m_requestMessage->setText(QStringLiteral("If the account exists, a reset link was sent."));
    m_requestMessage->show();
}

void ForgotPasswordWidget::doRecover()
{
    m_recoverMessage->hide();
    if (m_recoveryToken->text().isEmpty() || m_newPassword->text().isEmpty()) {
        return;
    }

    const QJsonObject body{{"lost_pass_token", m_recoveryToken->text()}, {"new_pass", m_newPassword->text()}};
    m_api->postJson("/api/pwmanage/recover_password/", QString(), body, [this](const QJsonValue &result, int) {
        // The backend always returns true regardless of outcome, matching the web client.
        Q_UNUSED(result)
        m_recoverMessage->setStyleSheet("color: green;");
        m_recoverMessage->setText(QStringLiteral("If the token was valid, your password has been changed. You can now log in."));
        m_recoverMessage->show();
        m_recoveryToken->clear();
        m_newPassword->clear();
    });
}
