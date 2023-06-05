package com.phynode1.Phynode1;

public class MyRequestData1 {
    private String jobId;
    private int requestType;
    private String requestPayload;

    public MyRequestData1(String jobId, int requestType, String requestPayload) {
        this.jobId = jobId;
        this.requestType = requestType;
        this.requestPayload = requestPayload;
    }

    public String getJobId() {
        return jobId;
    }

    public void setJobId(String jobId) {
        this.jobId = jobId;
    }

    public int getRequestType() {
        return requestType;
    }

    public void setRequestType(int requestType) {
        this.requestType = requestType;
    }

    public String getRequestPayload() {
        return requestPayload;
    }

    public void setRequestPayload(String requestPayload) {
        this.requestPayload = requestPayload;
    }
}
