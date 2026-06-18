import { TesseraClient, CallContext, TesseraWidgetConfig, VerificationResult, CallType } from './index';

// Web Widget Implementation
export class TesseraWidget {
  private container: HTMLElement;
  private config: TesseraWidgetConfig;
  private client: TesseraClient;

  constructor(
    container: HTMLElement | string,
    config: TesseraWidgetConfig = {}
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

    this.client = TesseraClient.getInstance();
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
    widget.className = `tessera-widget tessera-${this.config.theme} tessera-${this.config.size}`;

    if (this.config.position) {
      widget.classList.add(`tessera-${this.config.position}`);
    }

    // Apply custom styles
    if (this.config.customStyles) {
      Object.assign(widget.style, this.config.customStyles);
    }

    return widget;
  }

  private showLoadingState(widget: HTMLElement, callContext: CallContext): void {
    widget.innerHTML = `
      <div class="tessera-content tessera-loading">
        <div class="tessera-header">
          <div class="tessera-spinner"></div>
          <span class="tessera-status">Verifying ${this.getCallTypeDisplayName(callContext.callType)}...</span>
        </div>
        <div class="tessera-subtext">Tessera Security Check</div>
      </div>
    `;
  }

  private showResult(widget: HTMLElement, result: VerificationResult): void {
    const statusClass = result.isVerified ? 'verified' : 'unverified';
    const icon = result.isVerified ? '✓' : '⚠';
    const statusText = result.isVerified ? 'Verified Call' : 'Unverified Call';

    let content = `
      <div class="tessera-content tessera-${statusClass}">
        <div class="tessera-header">
          <span class="tessera-icon">${icon}</span>
          <span class="tessera-status">${statusText}</span>
    `;

    if (this.config.showVerificationBadge && result.confidence) {
      content += `<span class="tessera-badge">${result.confidence}</span>`;
    }

    content += '</div>';

    // Add caller info if available
    if (result.callerInfo) {
      if (this.config.showOrganization && result.callerInfo.organization) {
        content += `<div class="tessera-organization">${result.callerInfo.organization}</div>`;
      }

      if (result.callerInfo.displayName) {
        content += `<div class="tessera-name">${result.callerInfo.displayName}</div>`;
      }

      if (this.config.showTrustScore && result.callerInfo.trustScore !== undefined) {
        const trustPercent = Math.round(result.callerInfo.trustScore * 100);
        content += `
          <div class="tessera-trust-score">
            <span class="tessera-trust-label">Trust Score:</span>
            <div class="tessera-trust-bar">
              <div class="tessera-trust-fill" style="width: ${trustPercent}%"></div>
            </div>
            <span class="tessera-trust-percent">${trustPercent}%</span>
          </div>
        `;
      }
    } else if (!result.isVerified) {
      content += `<div class="tessera-subtext">This ${this.getCallTypeDisplayName(result.callType)} could not be verified</div>`;
    }

    content += '<div class="tessera-powered">Tessera Protected</div>';
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
      <div class="tessera-content tessera-error">
        <div class="tessera-header">
          <span class="tessera-icon">✕</span>
          <span class="tessera-status">Verification Error</span>
        </div>
        <div class="tessera-subtext">${message}</div>
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
    if (document.getElementById('tessera-widget-styles')) {
      return;
    }

    const styles = document.createElement('style');
    styles.id = 'tessera-widget-styles';
    styles.textContent = `
      .tessera-widget {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        max-width: 300px;
        z-index: 10000;
        position: relative;
      }

      .tessera-widget.tessera-light {
        background: rgba(255, 255, 255, 0.95);
        color: #333;
        border: 1px solid rgba(0, 0, 0, 0.1);
      }

      .tessera-widget.tessera-dark {
        background: rgba(30, 30, 30, 0.95);
        color: #fff;
        border: 1px solid rgba(255, 255, 255, 0.1);
      }

      .tessera-widget.tessera-auto {
        background: rgba(255, 255, 255, 0.95);
        color: #333;
        border: 1px solid rgba(0, 0, 0, 0.1);
      }

      @media (prefers-color-scheme: dark) {
        .tessera-widget.tessera-auto {
          background: rgba(30, 30, 30, 0.95);
          color: #fff;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
      }

      .tessera-widget.tessera-small {
        font-size: 12px;
        padding: 12px;
      }

      .tessera-widget.tessera-medium {
        font-size: 14px;
        padding: 16px;
      }

      .tessera-widget.tessera-large {
        font-size: 16px;
        padding: 20px;
      }

      .tessera-content {
        position: relative;
      }

      .tessera-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
      }

      .tessera-icon {
        font-size: 1.2em;
        font-weight: bold;
      }

      .tessera-status {
        font-weight: 600;
        flex: 1;
      }

      .tessera-badge {
        background: rgba(0, 0, 0, 0.1);
        padding: 2px 6px;
        border-radius: 8px;
        font-size: 0.8em;
        font-weight: 500;
        text-transform: uppercase;
      }

      .tessera-verified .tessera-icon {
        color: #4CAF50;
      }

      .tessera-verified .tessera-status {
        color: #4CAF50;
      }

      .tessera-verified .tessera-badge {
        background: rgba(76, 175, 80, 0.2);
        color: #4CAF50;
      }

      .tessera-unverified .tessera-icon {
        color: #FF9800;
      }

      .tessera-error .tessera-icon {
        color: #F44336;
      }

      .tessera-error .tessera-status {
        color: #F44336;
      }

      .tessera-organization {
        font-weight: 500;
        margin-bottom: 4px;
      }

      .tessera-name {
        font-size: 0.9em;
        opacity: 0.8;
        margin-bottom: 8px;
      }

      .tessera-subtext {
        font-size: 0.9em;
        opacity: 0.7;
        margin-bottom: 8px;
      }

      .tessera-trust-score {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        font-size: 0.8em;
      }

      .tessera-trust-label {
        opacity: 0.7;
      }

      .tessera-trust-bar {
        flex: 1;
        height: 4px;
        background: rgba(0, 0, 0, 0.1);
        border-radius: 2px;
        overflow: hidden;
      }

      .tessera-trust-fill {
        height: 100%;
        background: #4CAF50;
        transition: width 0.3s ease;
      }

      .tessera-trust-percent {
        opacity: 0.7;
        min-width: 30px;
        text-align: right;
      }

      .tessera-powered {
        font-size: 0.75em;
        opacity: 0.5;
        text-align: right;
        margin-top: 8px;
      }

      .tessera-spinner {
        width: 16px;
        height: 16px;
        border: 2px solid rgba(0, 0, 0, 0.1);
        border-left-color: #4CAF50;
        border-radius: 50%;
        animation: tessera-spin 1s linear infinite;
      }

      @keyframes tessera-spin {
        to {
          transform: rotate(360deg);
        }
      }

      /* Position utilities */
      .tessera-top-left {
        position: fixed;
        top: 20px;
        left: 20px;
      }

      .tessera-top-right {
        position: fixed;
        top: 20px;
        right: 20px;
      }

      .tessera-bottom-left {
        position: fixed;
        bottom: 20px;
        left: 20px;
      }

      .tessera-bottom-right {
        position: fixed;
        bottom: 20px;
        right: 20px;
      }

      .tessera-center {
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
export function createTesseraWidget(
  container: HTMLElement | string,
  config?: TesseraWidgetConfig
): TesseraWidget {
  return new TesseraWidget(container, config);
}

// Auto-initialization for script tag usage
if (typeof window !== 'undefined') {
  // @ts-ignore
  window.TesseraWidget = TesseraWidget;
  // @ts-ignore
  window.createTesseraWidget = createTesseraWidget;
}