package main

import (
	"context"
	"fmt"
	"os"

	"github.com/ykdynamics/forgeops-capabilities/sdk"
)

type input struct {
	Service string `json:"service"`
}

type result struct {
	Service string `json:"service"`
	Status  string `json:"status"`
	Items   int    `json:"items"`
}

func main() {
	addr := ":8099"
	if len(os.Args) >= 2 && os.Args[1] == "healthcheck" {
		sdk.HealthcheckMain(addr)
	}

	if err := sdk.Serve(addr, func(ctx context.Context, rc *sdk.Context) (any, error) {
		var in input
		if err := rc.Bind(&in); err != nil {
			return nil, sdk.NewError(sdk.ClassInvalidInput, "input: %v", err)
		}
		if in.Service != "acme-service" {
			return nil, sdk.RefuseUndeclaredTarget("service", in.Service)
		}

		// This is intentionally boring. Replace this with one bounded read from
		// your own system. The important part is that the requester cannot turn
		// it into a shell, choose a new target, or widen what the operation means.
		return result{Service: in.Service, Status: "ok", Items: 17}, nil
	}); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
