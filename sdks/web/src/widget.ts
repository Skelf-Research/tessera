import { CallDNSClient, CallContext, CallDNSWidgetConfig, VerificationResult, CallType } from './index';

// Web Widget Implementation
export class CallDNSWidget {
  private container: HTMLElement;
  private config: CallDNSWidgetConfig;
  private client: CallDNSClient;

  constructor(
    container: HTMLElement | string,
    config: CallDNSWidgetConfig = {}
  ) {
    this.container = typeof container === 'string'
      ? document.getElementById(container)!
      : container;

    if (!this.container) {
      throw new Error('Container element not found');
    }

    this.config = {
      showTrustScore: true,
      showOrganization: true,
      showVerificationBadge: true,
      autoVerify: true,
      theme: 'auto',
      position: 'top-right',
      size: 'medium',
      ...config,
    };

    this.client = CallDNSClient.getInstance();
    this.setupStyles();
  }

  public async show(callContext: CallContext): Promise<VerificationResult> {
    // Clear previous content
    this.container.innerHTML = '';

    // Create widget structure
    const widget = this.createWidget();
    this.container.appendChild(widget);

    // Show loading state
    this.showLoadingState(widget, callContext);

    try {
      // Perform verification
      const result = await this.client.verifyIncomingCall(callContext);

      // Update widget with result
      this.showResult(widget, result);

      return result;
    } catch (error) {
      this.showError(widget, error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  }

  public hide(): void {
    this.container.innerHTML = '';
  }

  private createWidget(): HTMLElement {
    const widget = document.createElement('div');
    widget.className = `calldns-widget calldns-${this.config.theme} calldns-${this.config.size}`;

    if (this.config.position) {
      widget.classList.add(`calldns-${this.config.position}`);
    }

    // Apply custom styles
    if (this.config.customStyles) {
      Object.assign(widget.style, this.config.customStyles);
    }

    return widget;
  }

  private showLoadingState(widget: HTMLElement, callContext: CallContext): void {
    widget.innerHTML = `
      <div class="calldns-content calldns-loading">
        <div class="calldns-header">
          <div class="calldns-spinner"></div>
          <span class="calldns-status">Verifying ${this.getCallTypeDisplayName(callContext.callType)}...</span>
        </div>
        <div class="calldns-subtext">CallDNS Security Check</div>
      </div>
    `;
  }

  private showResult(widget: HTMLElement, result: VerificationResult): void {
    const statusClass = result.isVerified ? 'verified' : 'unverified';
    const icon = result.isVerified ? '✓' : '⚠';
    const statusText = result.isVerified ? 'Verified Call' : 'Unverified Call';

    let content = `
      <div class="calldns-content calldns-${statusClass}">
        <div class="calldns-header">
          <span class="calldns-icon">${icon}</span>
          <span class="calldns-status">${statusText}</span>
    `;

    if (this.config.showVerificationBadge && result.confidence) {
      content += `<span class="calldns-badge">${result.confidence}</span>`;
    }

    content += '</div>';

    // Add caller info if available
    if (result.callerInfo) {
      if (this.config.showOrganization && result.callerInfo.organization) {
        content += `<div class="calldns-organization">${result.callerInfo.organization}</div>`;
      }

      if (result.callerInfo.displayName) {
        content += `<div class="calldns-name">${result.callerInfo.displayName}</div>`;
      }

      if (this.config.showTrustScore && result.callerInfo.trustScore !== undefined) {
        const trustPercent = Math.round(result.callerInfo.trustScore * 100);
        content += `
          <div class="calldns-trust-score">
            <span class="calldns-trust-label">Trust Score:</span>
            <div class="calldns-trust-bar">
              <div class="calldns-trust-fill" style="width: ${trustPercent}%"></div>
            </div>
            <span class="calldns-trust-percent">${trustPercent}%</span>
          </div>
        `;
      }
    } else if (!result.isVerified) {
      content += `<div class="calldns-subtext">This ${this.getCallTypeDisplayName(result.callType)} could not be verified</div>`;
    }

    content += '<div class="calldns-powered">CallDNS Protected</div>';
    content += '</div>';

    widget.innerHTML = content;

    // Add fade-in animation
    widget.style.opacity = '0';
    widget.style.transform = 'translateY(-10px)';

    requestAnimationFrame(() => {
      widget.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      widget.style.opacity = '1';
      widget.style.transform = 'translateY(0)';
    });
  }

  private showError(widget: HTMLElement, message: string): void {
    widget.innerHTML = `
      <div class="calldns-content calldns-error">
        <div class="calldns-header">
          <span class="calldns-icon">✕</span>
          <span class="calldns-status">Verification Error</span>
        </div>
        <div class="calldns-subtext">${message}</div>
      </div>
    `;
  }

  private getCallTypeDisplayName(callType: CallType): string {
    switch (callType) {
      case CallType.VOICE_CALL:
        return 'voice call';
      case CallType.VIDEO_CALL:
        return 'video call';
      case CallType.VOIP_CALL:
        return 'VoIP call';
      case CallType.WEBRTC_CALL:
        return 'WebRTC call';
      case CallType.IN_APP_CALL:
        return 'app call';
      case CallType.CONFERENCE_CALL:
        return 'conference call';
      case CallType.SCREEN_SHARE:
        return 'screen share';
      default:
        return 'call';
    }
  }

  private setupStyles(): void {
    // Check if styles are already added
    if (document.getElementById('calldns-widget-styles')) {
      return;
    }

    const styles = document.createElement('style');
    styles.id = 'calldns-widget-styles';
    styles.textContent = `
      .calldns-widget {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        max-width: 300px;
        z-index: 10000;
        position: relative;
      }

      .calldns-widget.calldns-light {
        background: rgba(255, 255, 255, 0.95);
        color: #333;
        border: 1px solid rgba(0, 0, 0, 0.1);
      }

      .calldns-widget.calldns-dark {
        background: rgba(30, 30, 30, 0.95);
        color: #fff;
        border: 1px solid rgba(255, 255, 255, 0.1);
      }

      .calldns-widget.calldns-auto {
        background: rgba(255, 255, 255, 0.95);
        color: #333;
        border: 1px solid rgba(0, 0, 0, 0.1);
      }

      @media (prefers-color-scheme: dark) {
        .calldns-widget.calldns-auto {
          background: rgba(30, 30, 30, 0.95);
          color: #fff;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
      }

      .calldns-widget.calldns-small {
        font-size: 12px;
        padding: 12px;
      }

      .calldns-widget.calldns-medium {
        font-size: 14px;
        padding: 16px;
      }

      .calldns-widget.calldns-large {
        font-size: 16px;
        padding: 20px;
      }

      .calldns-content {
        position: relative;
      }

      .calldns-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
      }

      .calldns-icon {
        font-size: 1.2em;
        font-weight: bold;
      }

      .calldns-status {
        font-weight: 600;
        flex: 1;
      }

      .calldns-badge {
        background: rgba(0, 0, 0, 0.1);
        padding: 2px 6px;
        border-radius: 8px;
        font-size: 0.8em;
        font-weight: 500;
        text-transform: uppercase;
      }

      .calldns-verified .calldns-icon {
        color: #4CAF50;
      }

      .calldns-verified .calldns-status {
        color: #4CAF50;
      }

      .calldns-verified .calldns-badge {
        background: rgba(76, 175, 80, 0.2);
        color: #4CAF50;
      }

      .calldns-unverified .calldns-icon {
        color: #FF9800;
      }

      .calldns-error .calldns-icon {
        color: #F44336;
      }

      .calldns-error .calldns-status {
        color: #F44336;
      }

      .calldns-organization {
        font-weight: 500;
        margin-bottom: 4px;
      }

      .calldns-name {
        font-size: 0.9em;
        opacity: 0.8;
        margin-bottom: 8px;
      }

      .calldns-subtext {
        font-size: 0.9em;
        opacity: 0.7;
        margin-bottom: 8px;
      }

      .calldns-trust-score {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        font-size: 0.8em;
      }

      .calldns-trust-label {
        opacity: 0.7;
      }

      .calldns-trust-bar {
        flex: 1;
        height: 4px;
        background: rgba(0, 0, 0, 0.1);
        border-radius: 2px;
        overflow: hidden;
      }

      .calldns-trust-fill {
        height: 100%;
        background: #4CAF50;
        transition: width 0.3s ease;
      }

      .calldns-trust-percent {
        opacity: 0.7;
        min-width: 30px;
        text-align: right;
      }

      .calldns-powered {
        font-size: 0.75em;
        opacity: 0.5;
        text-align: right;
        margin-top: 8px;
      }

      .calldns-spinner {
        width: 16px;
        height: 16px;
        border: 2px solid rgba(0, 0, 0, 0.1);
        border-left-color: #4CAF50;
        border-radius: 50%;
        animation: calldns-spin 1s linear infinite;
      }

      @keyframes calldns-spin {
        to {
          transform: rotate(360deg);
        }
      }

      /* Position utilities */
      .calldns-top-left {
        position: fixed;
        top: 20px;
        left: 20px;
      }

      .calldns-top-right {
        position: fixed;
        top: 20px;
        right: 20px;
      }

      .calldns-bottom-left {
        position: fixed;
        bottom: 20px;
        left: 20px;
      }

      .calldns-bottom-right {
        position: fixed;
        bottom: 20px;
        right: 20px;
      }

      .calldns-center {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
      }
    `;

    document.head.appendChild(styles);
  }
}

// Convenience function for quick widget creation
export function createCallDNSWidget(
  container: HTMLElement | string,
  config?: CallDNSWidgetConfig
): CallDNSWidget {
  return new CallDNSWidget(container, config);
}

// Auto-initialization for script tag usage
if (typeof window !== 'undefined') {
  // @ts-ignore
  window.CallDNSWidget = CallDNSWidget;
  // @ts-ignore
  window.createCallDNSWidget = createCallDNSWidget;
}