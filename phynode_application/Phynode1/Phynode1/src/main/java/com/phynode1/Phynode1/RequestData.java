package com.phynode1.Phynode1;

public class RequestData {
        private String jobId;
        private int requestType;
        private int addr;
        private int module;

        // Constructors
        public RequestData() {
        }

        public RequestData(String jobId, int requestType, int addr, int module) {
            this.jobId = jobId;
            this.requestType = requestType;
            this.addr = addr;
            this.module = module;
        }

        // Getters and setters
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

        public int getAddr() {
            return addr;
        }

        public void setAddr(int addr) {
            this.addr = addr;
        }

        public int getModule() {
            return module;
        }

        public void setModule(int module) {
            this.module = module;
        }
    }
